"""Read-only case archive for the Dify detective game."""

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
from urllib.parse import parse_qs, urlsplit

import pymysql


ROOT = Path(__file__).resolve().parent
DATABASE = 'dify_night_archive'


def connect(database=None):
    return pymysql.connect(
        host=os.environ.get('SEEKDB_HOST', '127.0.0.1'),
        port=int(os.environ.get('SEEKDB_PORT', '2881')),
        user=os.environ.get('SEEKDB_USER', 'root'),
        password=os.environ.get('SEEKDB_PASSWORD', ''),
        database=database, charset='utf8mb4', connect_timeout=5, read_timeout=5,
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
        cur.execute('DELETE FROM case_clues')
        cur.executemany('INSERT INTO case_clues VALUES (%s,%s,%s,%s)', case['facts'])
        cur.execute('REPLACE INTO case_verdict VALUES (1,%s,%s)', case['verdict'])
        db.commit()


def lookup(action, query):
    with connect(DATABASE) as db, db.cursor(pymysql.cursors.DictCursor) as cur:
        if action == '指认':
            cur.execute('SELECT culprit, explanation FROM case_verdict WHERE id=1')
            return cur.fetchone() or {}
        terms = ' '.join(re.findall(r'[\w]+', query)[:12])
        if not terms:
            return {'facts': []}
        cur.execute('SELECT id, title, body FROM case_clues '
                    'WHERE MATCH(search_text) AGAINST (%s) > 0 '
                    'ORDER BY MATCH(search_text) AGAINST (%s) DESC, id LIMIT 3', (terms, terms))
        return {'facts': cur.fetchall()}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        url = urlsplit(self.path)
        try:
            fields = parse_qs(url.query, max_num_fields=10) if len(url.query) <= 2000 else {}
        except ValueError:
            return self.respond(400, {'error': 'Too many query fields'})
        action = fields.get('action', [''])[0]
        query = fields.get('query', [''])[0].strip()
        if url.path != '/archive':
            return self.respond(404, {'error': 'Unknown endpoint'})
        if action not in ('调查', '指认') or len(query) > 120:
            return self.respond(400, {'error': 'Invalid action or query'})
        try:
            return self.respond(200, lookup(action, query))
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
        host = os.environ.get('ARCHIVE_HOST', '127.0.0.1')
        port = int(os.environ.get('ARCHIVE_PORT', '8765'))
        with ThreadingHTTPServer((host, port), Handler) as server:
            print(f'Case archive listening on {host}:{port}', flush=True)
            server.serve_forever()
