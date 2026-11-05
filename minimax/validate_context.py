"""Reproduce the context requirements without claiming MiniMax participation."""

import argparse
import hashlib
from importlib.metadata import distributions
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

import pymysql


HERE = Path(__file__).resolve().parent
REQUIRED = {'policy.md', 'loan.py', 'test_loan.py'}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', required=True, help='Dedicated sdd_ sample database; its documents are replaced')
    parser.add_argument('--output', type=Path, required=True, help='New evidence directory')
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    state_path = output / 'memory.db'
    report = {'context_validation_complete': False, 'contest_ready': False,
              'minimax_called': False, 'target_fix_complete': False, 'commands': [],
              'python': platform.python_version(),
              'packages': {d.metadata['Name']: d.version for d in distributions()},
              'source_sha256': {str(p.relative_to(HERE)): digest(p)
                                for p in [HERE / 'sdd.py', HERE / 'request_patch.py',
                                          HERE / 'validate_context.py', HERE / 'requirements.txt',
                                          HERE / 'requirements.lock', *sorted((HERE / 'fixture').glob('*.*'))]
                                if p.is_file()}}

    def save():
        (output / 'summary.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')

    def run(name, arguments, expected_exit=0):
        command = [sys.executable, *arguments]
        result = subprocess.run(command, cwd=HERE, capture_output=True, text=True, timeout=120)
        (output / (name + '.stdout')).write_text(result.stdout)
        (output / (name + '.stderr')).write_text(result.stderr)
        report['commands'].append({'stage': name, 'command': command, 'exit_code': result.returncode})
        save()
        if result.returncode != expected_exit:
            raise RuntimeError(f'{name} exited {result.returncode}; inspect its saved logs')
        return result

    def sdd(name, arguments):
        result = run(name, ['sdd.py', '--database', args.database, '--state', str(state_path), *arguments])
        value = json.loads(result.stdout)
        (output / (name + '.json')).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
        return value

    def check_context(value, root):
        sources = {s['path']: s for s in value['sources']}
        if not REQUIRED <= sources.keys() or len(value['database_queries']) != 3:
            raise RuntimeError('Missing necessary source or actual database-query records')
        for name, source in sources.items():
            if source['body'] != (root / name).read_text() or source['digest'] != digest(root / name):
                raise RuntimeError('Retrieved body or digest does not match the imported file')
        return sources

    changed_database = False
    try:
        save()
        with pymysql.connect(host=os.environ.get('SEEKDB_HOST', '127.0.0.1'),
                             port=int(os.environ.get('SEEKDB_PORT', '2881')),
                             user=os.environ.get('SEEKDB_USER', 'root'),
                             password=os.environ.get('SEEKDB_PASSWORD', ''),
                             charset='utf8mb4', connect_timeout=10, read_timeout=30) as db:
            with db.cursor() as cursor:
                cursor.execute('SELECT VERSION()')
                report['database_version'] = cursor.fetchone()[0]
        sdd('ingest', ['ingest'])
        initial = sdd('initial-context', ['prepare', 'renewal'])
        sources = check_context(initial, HERE / 'fixture')
        if initial['powercontext_progress']:
            raise RuntimeError('Validation must start with empty task state')
        baseline = run('baseline-tests', ['-m', 'unittest', 'discover', '-s', 'fixture', '-v'], expected_exit=1)
        if not all(s in baseline.stderr for s in ['FAIL: test_member_renewal', '14 != 21',
                                                  'Ran 3 tests', 'FAILED (failures=1)']):
            raise RuntimeError('Baseline must fail because of the specified behavior, not an environment error')
        done = 'Reproduced the missing member renewal behavior'
        verification = 'Same three tests: member renewal 14 != 21; ordinary and reservation behavior pass'
        remembered = sdd('remember', ['remember', '--done', done,
                                     '--next', 'Use MiniMax to implement member renewal while preserving the tests',
                                     '--verification', verification])
        resumed = sdd('resumed-context', ['prepare', 'renewal'])
        check_context(resumed, HERE / 'fixture')
        if not any(p['state']['done'] == done and p['state']['verification'] == verification
                   and p['citation'] == remembered['citation'] for p in resumed['powercontext_progress']):
            raise RuntimeError('The independent prepare process did not reuse the saved task state')
        updated_root = output / 'updated-fixture'
        shutil.copytree(HERE / 'fixture', updated_root, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        policy = updated_root / 'policy.md'
        body = policy.read_text()
        if body.count('21-day') != 1:
            raise RuntimeError('Unexpected baseline specification')
        policy.write_text(body.replace('21-day', '28-day'))
        changed_database = True
        sdd('updated-ingest', ['ingest', '--root', str(updated_root)])
        updated = sdd('updated-context', ['prepare', 'renewal'])
        updated_sources = check_context(updated, updated_root)
        if updated_sources['policy.md']['digest'] == sources['policy.md']['digest']:
            raise RuntimeError('The updated specification was not retrieved')
        sdd('restore-ingest', ['ingest'])
        changed_database = False
        final = sdd('model-ready-context', ['prepare', 'renewal'])
        check_context(final, HERE / 'fixture')
        if any(digest(HERE / name) != sha for name, sha in report['source_sha256'].items()):
            raise RuntimeError('Source or tests changed during validation')
        report.update(context_validation_complete=True,
                      verified_requirements=['runnable context module', 'correct and refreshed context',
                                             'real seekdb queries', 'PowerContext reuse after process restart'],
                      remaining_requirements=['actual MiniMax code generation or modification',
                                              'unchanged target and regression tests pass after that modification'])
        save()
        print(json.dumps({'context_validation_complete': True, 'contest_ready': False,
                          'minimax_called': False, 'summary': str(output / 'summary.json')}, indent=2))
    except Exception as error:
        report['error'] = f'{type(error).__name__}: {error}'
        save()
        raise
    finally:
        if changed_database:
            sdd('restore-after-failure', ['ingest'])


if __name__ == '__main__':
    main()
