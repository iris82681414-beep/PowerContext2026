import { createHash } from 'node:crypto';
import { readFile } from 'node:fs/promises';
import { createServer } from 'node:http';
import { dirname, extname, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';
import { performance } from 'node:perf_hooks';
import { Schema, SeekdbClient, VectorIndexConfig } from 'seekdb';

const dist = resolve(dirname(fileURLToPath(import.meta.url)), 'dist');
const namePattern = /^[a-z][a-z0-9_]{0,27}$/;
const profileNames = new Set(['fp32', 'fp16', 'q8']);
const database = process.env.SEEKDB_DATABASE || 'stepfun_kb';
if (!namePattern.test(database)) throw new Error('Invalid SEEKDB_DATABASE name');

const connection = {
  host: process.env.SEEKDB_HOST || '127.0.0.1',
  port: Number(process.env.SEEKDB_PORT || 2881),
  user: process.env.SEEKDB_USER || 'root',
  password: process.env.SEEKDB_PASSWORD || '',
  queryTimeout: 30_000,
};
const bootstrap = new SeekdbClient({ ...connection, database: 'test' });
try {
  await bootstrap.execute('CREATE DATABASE IF NOT EXISTS `' + database + '`');
} finally {
  await bootstrap.close();
}
const client = new SeekdbClient({ ...connection, database });
const schema = new Schema({
  vectorIndex: new VectorIndexConfig({ hnsw: { dimension: 384, distance: 'cosine' }, embeddingFunction: null }),
});

// The SDK's hybrid search uses a database session variable. Keep SDK operations serial.
let pending = Promise.resolve();
function databaseOperation(operation) {
  const result = pending.then(operation);
  pending = result.catch(() => {});
  return result;
}

class InvalidInput extends Error {}

function collectionName({ library, profile }) {
  if (typeof library !== 'string' || !namePattern.test(library) || !profileNames.has(profile)) {
    throw new InvalidInput('Invalid library or model profile');
  }
  return `pocket_v1_${library}_${profile}`;
}

function assertVector(vector) {
  if (!Array.isArray(vector) || vector.length !== 384 || !vector.every(Number.isFinite)) {
    throw new InvalidInput('Expected a finite 384-dimensional browser embedding');
  }
  const squaredNorm = vector.reduce((sum, value) => sum + value * value, 0);
  if (Math.abs(squaredNorm - 1) > 0.03) throw new InvalidInput('Expected a unit-length embedding');
}

function validateDocument(record) {
  if (typeof record?.title !== 'string' || !record.title.trim() || record.title.length > 160 ||
      typeof record.text !== 'string' || !record.text.trim() || Buffer.byteLength(record.text) > 8000) {
    throw new InvalidInput('Every document needs a title and a nonempty text chunk of at most 8000 bytes');
  }
  assertVector(record.embedding);
}

async function importDocuments(body) {
  const name = collectionName(body);
  const docs = body.documents;
  if (!Array.isArray(docs) || docs.length < 1 || docs.length > 32) throw new InvalidInput('Import 1 to 32 chunks at a time');
  docs.forEach(validateDocument);
  const unique = new Map(docs.map((doc) => [createHash('sha256').update(JSON.stringify([doc.title, doc.text])).digest('hex'), doc]));
  return databaseOperation(async () => {
    const collection = await client.hasCollection(name)
      ? await client.getCollection({ name, embeddingFunction: null })
      : await client.createCollection({ name, schema });
    const started = performance.now();
    await collection.upsert({
      ids: [...unique.keys()],
      documents: [...unique.values()].map((doc) => doc.text),
      metadatas: [...unique.values()].map((doc) => ({ title: doc.title })),
      embeddings: [...unique.values()].map((doc) => doc.embedding),
    });
    const written = performance.now();
    await collection.refresh_index();
    return { count: Number(await collection.count()), written: unique.size,
      writeMs: written - started, refreshMs: performance.now() - written };
  });
}

async function search(body) {
  const name = collectionName(body);
  assertVector(body.embedding);
  const words = typeof body.query === 'string' && body.query.length <= 600
    ? (body.query.match(/[\p{L}\p{N}]+/gu) || []).slice(0, 16).join(' ')
    : '';
  if (!words) throw new InvalidInput('Enter a query with at least one searchable word');
  return databaseOperation(async () => {
    if (!await client.hasCollection(name)) return { results: [], searchMs: 0 };
    const collection = await client.getCollection({ name, embeddingFunction: null });
    const started = performance.now();
    const matches = await collection.hybridSearch({
      query: { whereDocument: { $contains: words }, nResults: 24 },
      knn: { queryEmbeddings: [body.embedding], nResults: 24 },
      rank: { rrf: { rankWindowSize: 24, rankConstant: 60 } },
      nResults: 5,
      include: ['documents', 'metadatas'],
    });
    const searchMs = performance.now() - started;
    const results = (matches.ids[0] || []).map((id, index) => ({
      id, title: matches.metadatas?.[0]?.[index]?.title || id, text: matches.documents?.[0]?.[index] || '',
    }));
    return { results, searchMs };
  });
}

async function readJson(request) {
  const pieces = [];
  let size = 0;
  for await (const piece of request) {
    size += piece.length;
    if (size > 900_000) throw new InvalidInput('Request is too large');
    pieces.push(piece);
  }
  let body;
  try { body = JSON.parse(Buffer.concat(pieces).toString('utf8')); }
  catch { throw new InvalidInput('Expected a JSON request'); }
  if (!body || typeof body !== 'object' || Array.isArray(body)) throw new InvalidInput('Expected a JSON object');
  return body;
}

const routes = {
  '/api/import': importDocuments,
  '/api/search': search,
  '/api/count': async (body) => {
    const name = collectionName(body);
    return databaseOperation(async () => ({ count: await client.hasCollection(name)
      ? Number(await (await client.getCollection({ name, embeddingFunction: null })).count()) : 0 }));
  },
};
const mime = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8', '.wasm': 'application/wasm', '.json': 'application/json' };

const server = createServer(async (request, response) => {
  const json = (status, data) => {
    response.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' });
    response.end(JSON.stringify(data));
  };
  try {
    const path = new URL(request.url, 'http://localhost').pathname;
    if (path.startsWith('/api/')) {
      if (request.method !== 'POST' || !Object.hasOwn(routes, path)) return json(404, { error: 'Unknown endpoint' });
      if (!request.headers['content-type']?.startsWith('application/json')) return json(415, { error: 'Expected JSON' });
      return json(200, await routes[path](await readJson(request)));
    }
    if (request.method !== 'GET') return json(405, { error: 'Method not allowed' });
    const file = resolve(dist, '.' + (path === '/' ? '/index.html' : decodeURIComponent(path)));
    if (!file.startsWith(dist + sep)) return json(404, { error: 'Asset not found' });
    const content = await readFile(file);
    response.writeHead(200, {
      'Content-Type': mime[extname(file)] || 'application/octet-stream',
      'Content-Length': content.length,
    });
    response.end(content);
  } catch (error) {
    if (error instanceof InvalidInput) return json(400, { error: error.message });
    if (error.code === 'ENOENT' || error.code === 'EISDIR') return json(404, { error: 'Asset not found; run npm run build' });
    console.error('Request failed:', error.name, error.code || 'database');
    return json(503, { error: 'seekdb request failed. Check the database connection and server log.' });
  }
});

const host = process.env.APP_HOST || '127.0.0.1';
const port = Number(process.env.APP_PORT || 8787);
server.listen(port, host, () => console.log(`Pocket Library listening on http://${host}:${port}`));
process.once('SIGTERM', () => server.close(() => void client.close()));
