"""Verify persistence through two independent HTTP server processes."""

import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def test_independent_process_restart(app, tmp_path):
    from app.database import db

    root = Path(__file__).resolve().parents[1]
    with app.app_context():
        version = db.fetch_one('SELECT VERSION() AS version')['version']
        ddl = db.fetch_one('SHOW CREATE TABLE documents')['Create Table']
    assert 'seekdb' in version.lower()
    assert 'FULLTEXT' in ddl.upper()
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    base = f'http://127.0.0.1:{port}'
    environment = dict(os.environ, HOST='127.0.0.1', PORT=str(port), FLASK_DEBUG='False',
                       SEEKDB_DATABASE=app.config['SEEKDB_DATABASE'])
    report = {'database_version': version, 'fulltext_index_ddl': ddl,
              'server_command': [sys.executable, '-m', 'app.main'], 'runs': [],
              'source_sha256': {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in sorted((root / 'app').rglob('*.py'))}}
    current = None
    handles = []

    def request(path, body=None, method=None):
        encoded = None if body is None else json.dumps(body, ensure_ascii=False).encode()
        req = Request(base + path, data=encoded, method=method,
                      headers={'Content-Type': 'application/json'})
        with urlopen(req, timeout=20) as response:
            return json.load(response)

    def start(label):
        nonlocal current
        log = (tmp_path / (label + '.log')).open('wb')
        handles.append(log)
        current = subprocess.Popen(report['server_command'], cwd=root, env=environment,
                                   stdout=log, stderr=subprocess.STDOUT)
        report['runs'].append({'label': label, 'pid': current.pid})
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if current.poll() is not None:
                raise AssertionError(f'Server exited with {current.returncode}; see {log.name}')
            try:
                request('/api/projects')
                return
            except OSError:
                time.sleep(0.1)
        raise AssertionError(f'Server did not become ready; see {log.name}')

    def stop():
        nonlocal current
        if current is not None:
            current.terminate()
            try:
                current.wait(timeout=10)
            except subprocess.TimeoutExpired:
                current.kill()
                current.wait(timeout=10)
            report['runs'][-1]['exit_code'] = current.returncode
            current = None

    try:
        start('before-restart')
        project = request('/api/projects', {'name': '独立进程验收项目'})
        document = request('/api/documents', {
            'project_id': project['id'], 'title': '真实重启验收资料',
            'content': '独立进程重启后仍须保留的真实资料，以及待办的原始引用。',
            'source_identifier': 'process-acceptance.txt'})
        todo = request('/api/todos', {
            'project_id': project['id'], 'document_id': document['id'],
            'title': '验证跨进程恢复', 'quoted_text': '独立进程重启',
            'status': 'in_progress'})
        report['before_restart'] = {'project': project, 'document': document, 'todo': todo}
        stop()
        start('after-restart')
        assert report['runs'][0]['pid'] != report['runs'][1]['pid']
        restored_document = request(f"/api/documents/{document['id']}")
        restored_todo = request(f"/api/todos/{todo['id']}")
        restored_project = request(f"/api/projects/{project['id']}")
        search = request('/api/search?' + urlencode({'q': '独立进程', 'project_id': project['id']}))
        assert restored_document['content'] == document['content']
        assert restored_todo['quoted_text'] == todo['quoted_text'] == '独立进程重启'
        assert restored_todo['status'] == 'in_progress'
        assert restored_todo['document_id'] == document['id']
        assert restored_project['id'] == project['id']
        assert search['count'] >= 1
        report['after_restart'] = {'project': restored_project, 'document': restored_document,
                                   'todo': restored_todo, 'search': search}
        report['independent_restart_passed'] = True
    finally:
        stop()
        for handle in handles:
            handle.close()
        output = Path(os.environ.get('QODER_RESTART_EVIDENCE', str(tmp_path / 'restart.json')))
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
