"""Case facts and persistent player notebooks for the Dify workflow."""

import argparse
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re

import pymysql

ROOT = Path(__file__).resolve().parent
DATABASE = 'dify_night_archive'


def connect(database=None):
    return pymysql.connect(
        host=os.environ.get('SEEKDB_HOST', '127.0.0.1'),
        port=int(os.environ.get('SEEKDB_PORT', '2881')),
        user=os.environ.get('SEEKDB_USER', 'root'),
        password=os.environ.get('SEEKDB_PASSWORD', ''),
        database=database, charset='utf8mb4', connect_timeout=5,
        read_timeout=5, write_timeout=5,
    )


def load_case():
    case = json.loads((ROOT / 'case.json').read_text(encoding='utf-8'))
    with connect() as db, db.cursor() as cur:
        cur.execute('CREATE DATABASE IF NOT EXISTS dify_night_archive')
    with connect(DATABASE) as db, db.cursor() as cur:
        cur.execute('CREATE TABLE IF NOT EXISTS case_clues (id VARCHAR(16) PRIMARY KEY, '
                    'title VARCHAR(100) NOT NULL, body TEXT NOT NULL, '
                    'search_text TEXT NOT NULL, FULLTEXT INDEX fact_search(search_text) WITH PARSER ngram)')
        cur.execute('CREATE TABLE IF NOT EXISTS case_verdict (id INT PRIMARY KEY, '
                    'culprit VARCHAR(40) NOT NULL, explanation TEXT NOT NULL)')
        cur.execute('CREATE TABLE IF NOT EXISTS player_notebooks ('
                    'session_id VARCHAR(64) PRIMARY KEY, revision BIGINT NOT NULL, '
                    'seen TEXT NOT NULL, attempts INT NOT NULL, completed TINYINT NOT NULL)')
        cur.execute('CREATE TABLE IF NOT EXISTS player_turns ('
                    'session_id VARCHAR(64), revision BIGINT, action VARCHAR(16), '
                    'query_text VARCHAR(120), decision VARCHAR(32), result_text TEXT, '
                    'PRIMARY KEY(session_id, revision))')
        for fact in case['facts']:
            cur.execute('REPLACE INTO case_clues VALUES (%s,%s,%s,%s)', fact)
        cur.execute('REPLACE INTO case_verdict VALUES (1,%s,%s)', case['verdict'])
        db.commit()


class Conflict(Exception):
    pass


def notebook(cur, session, lock=False):
    cur.execute('INSERT IGNORE INTO player_notebooks VALUES (%s,0,%s,0,0)', (session, '[]'))
    cur.execute('SELECT revision, seen, attempts, completed FROM player_notebooks '
                'WHERE session_id=%s' + (' FOR UPDATE' if lock else ''), (session,))
    row = cur.fetchone()
    row['seen'] = json.loads(row['seen'])
    row['completed'] = bool(row['completed'])
    return row


def read_archive(fields, search):
    with connect(DATABASE) as db, db.cursor(pymysql.cursors.DictCursor) as cur:
        state = notebook(cur, fields['session'])
        facts = []
        if search:
            terms = ' '.join(re.findall(r'[\w]+', fields['query'])[:12])
            if terms:
                cur.execute('SELECT id,title,body FROM case_clues '
                            'WHERE MATCH(search_text) AGAINST (%s)>0 '
                            'ORDER BY MATCH(search_text) AGAINST (%s) DESC,id LIMIT 3', (terms, terms))
                facts = cur.fetchall()
        else:
            cur.execute('SELECT id,title,body FROM case_clues ORDER BY id')
            facts = [row for row in cur.fetchall() if row['id'] in state['seen']]
        cur.execute('SELECT culprit,explanation FROM case_verdict WHERE id=1')
        verdict = cur.fetchone()
        db.commit()
        return {'state': state, 'facts': facts, 'verdict': verdict}


def commit_turn(fields):
    action = fields.get('action')
    if action not in ('调查', '指认', '重开'):
        raise ValueError('Invalid action')
    with connect(DATABASE) as db, db.cursor(pymysql.cursors.DictCursor) as cur:
        state = notebook(cur, fields['session'], lock=True)
        if fields.get('revision') != state['revision']:
            raise Conflict('Notebook changed; repeat this action')
        decision = fields.get('decision', '')
        result = fields.get('result', '')
        if not isinstance(result, str) or not 0 < len(result) <= 6000:
            raise ValueError('Invalid result')
        if action == '重开':
            state.update(seen=[], attempts=0, completed=False)
        elif action == '调查':
            ids = fields.get('clues', [])
            if not isinstance(ids, list) or len(ids) > 6 or any(not isinstance(x, str) for x in ids):
                raise ValueError('Invalid clue list')
            cur.execute('SELECT id FROM case_clues')
            valid = {row['id'] for row in cur.fetchall()}
            if not set(ids).issubset(valid):
                raise ValueError('Unknown clue')
            state['seen'] = sorted(set(state['seen']) | set(ids))
        else:
            if decision not in ('insufficient', 'wrong', 'solved', 'already_solved'):
                raise ValueError('Invalid decision')
            if not state['completed']:
                state['attempts'] += 1
                state['completed'] = decision == 'solved'
        state['revision'] += 1
        cur.execute('UPDATE player_notebooks SET revision=%s,seen=%s,attempts=%s,completed=%s '
                    'WHERE session_id=%s', (state['revision'], json.dumps(state['seen']),
                                           state['attempts'], int(state['completed']), fields['session']))
        cur.execute('INSERT INTO player_turns VALUES (%s,%s,%s,%s,%s,%s)',
                    (fields['session'], state['revision'], action, fields['query'], decision, result))
        db.commit()
        return {'state': state, 'result': result}


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        token = os.environ['ARCHIVE_TOKEN']
        if not hmac.compare_digest(self.headers.get('Authorization', ''), 'Bearer ' + token):
            return self.respond(401, {'error': 'Archive authorization required'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 16384:
                raise ValueError('Invalid body length')
            fields = json.loads(self.rfile.read(length))
            if not isinstance(fields, dict):
                raise ValueError('Expected JSON object')
            if not isinstance(fields.get('session'), str) or not re.fullmatch(r'[A-Za-z0-9_-]{8,64}', fields['session']):
                raise ValueError('Invalid notebook name')
            if not isinstance(fields.get('query'), str) or len(fields['query']) > 120:
                raise ValueError('Invalid query')
            if self.path in ('/facts/search', '/notebook/read'):
                value = read_archive(fields, self.path == '/facts/search')
            elif self.path == '/notebook/commit':
                value = commit_turn(fields)
            else:
                return self.respond(404, {'error': 'Unknown endpoint'})
            return self.respond(200, value)
        except (ValueError, TypeError, KeyError):
            return self.respond(400, {'error': 'Invalid request'})
        except Conflict:
            return self.respond(409, {'error': 'Notebook changed; repeat this action'})
        except pymysql.MySQLError:
            return self.respond(503, {'error': 'Archive unavailable'})

    def respond(self, status, value):
        data = json.dumps(value, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format, *args):
        pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('init', 'serve'))
    args = parser.parse_args()
    if args.command == 'init':
        load_case()
    else:
        if len(os.environ.get('ARCHIVE_TOKEN', '')) < 32:
            raise SystemExit('Set ARCHIVE_TOKEN to a private random token of at least 32 characters')
        with ThreadingHTTPServer((os.environ.get('ARCHIVE_HOST', '127.0.0.1'),
                                  int(os.environ.get('ARCHIVE_PORT', '8765'))), Handler) as server:
            server.serve_forever()
