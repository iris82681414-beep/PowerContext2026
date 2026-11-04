"""Retrieve SDD evidence from seekdb and persist task progress with PowerContext."""

import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import re

import pymysql
from powercontext.builtin.artifacts.memory import MemoryEntryInput
from powercontext.builtin.persistence.sqlite import SQLiteConfig
from powercontext.builtin.runtime import BuiltinConfig, RememberMemoryRequest, open_builtin_runtime
from powercontext.builtin.scope import ScopeDraft


HERE = Path(__file__).resolve().parent
KINDS = {'.md': 'specification', '.py': 'source'}


def connect(database=None):
    return pymysql.connect(host=os.environ.get('SEEKDB_HOST', '127.0.0.1'),
                           port=int(os.environ.get('SEEKDB_PORT', '2881')),
                           user=os.environ.get('SEEKDB_USER', 'root'),
                           password=os.environ.get('SEEKDB_PASSWORD', ''),
                           database=database, charset='utf8mb4', connect_timeout=10)


def import_repository(root, database):
    records = []
    for path in sorted(root.iterdir()):
        if path.suffix not in KINDS or not path.is_file():
            continue
        kind = 'test' if path.name.startswith('test_') else KINDS[path.suffix]
        content = path.read_text(encoding='utf-8')
        records.append((path.name, kind, content, hashlib.sha256(content.encode()).hexdigest()))
    if not records:
        raise ValueError('No supported source, specification, or test files')
    with connect() as db, db.cursor() as cur:
        cur.execute('CREATE DATABASE IF NOT EXISTS `' + database + '`')
    with connect(database) as db, db.cursor() as cur:
        cur.execute('CREATE TABLE IF NOT EXISTS engineering_docs (path VARCHAR(255) PRIMARY KEY, '
                    'kind VARCHAR(32) NOT NULL, body TEXT NOT NULL, digest CHAR(64) NOT NULL, '
                    'FULLTEXT INDEX document_search(body))')
        cur.execute('DELETE FROM engineering_docs')
        cur.executemany('INSERT INTO engineering_docs VALUES (%s, %s, %s, %s)', records)
        db.commit()
    return {'database': 'seekdb', 'imported': [{'path': path, 'kind': kind, 'sha256': digest}
                                               for path, kind, _, digest in records]}


def retrieve(database, task):
    query = ' '.join(re.findall(r'[\w]+', task.lower())[:30])
    if not query:
        raise ValueError('A retrieval query needs at least one word')
    result = []
    with connect(database) as db, db.cursor(pymysql.cursors.DictCursor) as cur:
        for kind in ('specification', 'source', 'test'):
            cur.execute('SELECT path, kind, body, digest, MATCH(body) AGAINST (%s) AS score '
                        'FROM engineering_docs WHERE kind=%s AND MATCH(body) AGAINST (%s) > 0 '
                        'ORDER BY score DESC, path LIMIT 3', (query, kind, query))
            for row in cur.fetchall():
                row['score'] = float(row['score'])
                result.append(row)
    return result


async def progress(state_db, database, update=None):
    state_db.parent.mkdir(parents=True, exist_ok=True)
    config = BuiltinConfig(database=SQLiteConfig(url=f'sqlite+aiosqlite:///{state_db}'))
    async with open_builtin_runtime(config) as runtime:
        scope = await runtime.scopes.create(ScopeDraft(title='SDD loan renewal', summary='Engineering task progress',
                                                      idempotency_key=f'sdd-progress:{database}'))
        memory = runtime.memory.for_scope(scope.scope_id)
        if update is not None:
            reply = await memory.remember(RememberMemoryRequest(entries=(MemoryEntryInput(
                kind='fact', text=json.dumps(update, ensure_ascii=False)),)))
            return {'scope_id': scope.scope_id, 'citation': reply.entry.citation.model_dump(mode='json')}
        entries = await memory.list()
        return [{'state': json.loads(entry.entry.text), 'citation': entry.citation.model_dump(mode='json')}
                for entry in entries.entries]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', default='sdd_renewal')
    parser.add_argument('--state', type=Path, default=HERE / '.sdd-state' / 'memory.db')
    commands = parser.add_subparsers(dest='command', required=True)
    ingest = commands.add_parser('ingest')
    ingest.add_argument('--root', type=Path, default=HERE / 'fixture')
    prepare = commands.add_parser('prepare')
    prepare.add_argument('task')
    remember = commands.add_parser('remember')
    remember.add_argument('--done', required=True)
    remember.add_argument('--next', required=True)
    remember.add_argument('--verification', default='')
    args = parser.parse_args()
    if not re.fullmatch(r'sdd_[a-z][a-z0-9_]{0,22}', args.database):
        parser.error('Use a dedicated database with the sdd_ prefix')
    if args.command == 'ingest':
        result = import_repository(args.root, args.database)
    elif args.command == 'remember':
        result = asyncio.run(progress(args.state.resolve(), args.database,
                                      {'done': args.done, 'next': args.next, 'verification': args.verification}))
    else:
        sources = retrieve(args.database, args.task)
        if {item['kind'] for item in sources} != {'specification', 'source', 'test'}:
            parser.error('Refine the task so seekdb returns a specification, source file, and test')
        result = {'task': args.task, 'sources': sources,
                  'powercontext_progress': asyncio.run(progress(args.state.resolve(), args.database)),
                  'agent_instruction': 'Use these sources to modify the business module. Preserve the tests and public signature.'}
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
