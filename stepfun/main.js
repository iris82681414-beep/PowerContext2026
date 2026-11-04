import './style.css';
import { MODEL, REVISION, openDefaultEncoder, openEncoder } from './embedding.js';
import { documents, queries } from './sample.js';

const $ = (id) => document.getElementById(id);
const status = (message) => { $('status').textContent = message; };
const controls = [...document.querySelectorAll('input, textarea, button')].filter((element) => element.id !== 'download');
let encoder;
let library;
let report;

async function action(operation) {
  controls.forEach((element) => { element.disabled = true; });
  try { await operation(); }
  catch (error) { status(error.message); }
  finally { controls.forEach((element) => { element.disabled = false; }); }
}

async function api(route, body) {
  const response = await fetch(`/api/${route}`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || '请求失败');
  return result;
}

function context() {
  if (!encoder || !library) throw new Error('请先打开知识库。');
  return { library, profile: encoder.profile };
}

async function selectLibrary() {
  const name = $('library').value.trim();
  if (!/^[a-z][a-z0-9_]{0,27}$/.test(name)) throw new Error('知识库名以小写字母开头，可含数字和下划线。');
  if (!encoder) encoder = await openDefaultEncoder(status);
  const { count } = await api('count', { library: name, profile: encoder.profile });
  library = name;
  localStorage.setItem('pocket-library', library);
  $('results').replaceChildren();
  $('timing').textContent = '';
  $('backend').textContent = `${encoder.device.toUpperCase()} · ${encoder.profile.toUpperCase()}`;
  $('count').textContent = `${library} 中有 ${count} 个文本片段`;
  status('可以导入文本或开始检索。');
}

function splitDocument(title, text) {
  const characters = Array.from(text.trim());
  const parts = [];
  for (let offset = 0; offset < characters.length; offset += 960) {
    const chunk = characters.slice(offset, offset + 960).join('').trim();
    if (chunk) parts.push({ title: offset ? `${title.slice(0, 150)} · ${parts.length + 1}` : title, text: chunk });
  }
  return parts;
}

async function importBatch(records, model, name, batchSize = 8) {
  const vectors = [];
  const started = performance.now();
  for (let offset = 0; offset < records.length; offset += batchSize) {
    status(`浏览器向量化 ${offset}/${records.length}`);
    const batch = records.slice(offset, offset + batchSize);
    vectors.push(...await model.encode(batch.map((record) => record.text)));
  }
  const embeddingMs = performance.now() - started;
  const result = await api('import', { library: name, profile: model.profile,
    documents: records.map((record, index) => ({ ...record, embedding: vectors[index] })) });
  return { ...result, embeddingMs };
}

async function importIntoLibrary(records) {
  const { library: name } = context();
  if (records.length < 1 || records.length > 32) throw new Error('每次请导入 1 到 32 个文本片段。');
  const result = await importBatch(records, encoder, name);
  $('count').textContent = `${name} 中有 ${result.count} 个文本片段`;
  status(`已写入并刷新 ${result.written} 个片段。`);
}

async function searchFor(query, model, name) {
  const start = performance.now();
  const [embedding] = await model.encode([query]);
  const queryEmbeddingMs = performance.now() - start;
  const output = await api('search', { library: name, profile: model.profile, query, embedding });
  return { ...output, queryEmbeddingMs, endToEndMs: performance.now() - start };
}

const median = (values) => [...values].sort((a, b) => a - b)[Math.floor(values.length / 2)];

async function benchmark() {
  const run = { browser: navigator.userAgent, model: MODEL, revision: REVISION,
    documents: documents.length, queryCount: queries.length, variants: [] };
  for (const [profile, batch] of [['fp32', 1], ['q8', 1], ['q8', 8], ['fp16', 8]]) {
    let model;
    try { model = await openEncoder(profile, status); }
    catch (error) {
      if (profile !== 'fp16') throw error;
      run.variants.push({ profile, skipped: error.message });
      continue;
    }
    const variant = { profile, device: model.device, batch, loadMs: model.loadMs, reusedModel: model.cached, rounds: [] };
    for (let repetition = 0; repetition < 3; repetition++) {
      const name = `bench_${profile}_${crypto.randomUUID().slice(0, 8)}`;
      const imported = await importBatch(documents, model, name, batch);
      const outcomes = [];
      for (const { query, expectedTitle } of queries) {
        const { results, ...timings } = await searchFor(query, model, name);
        outcomes.push({ query, expectedTitle, titles: results.map((result) => result.title), ...timings });
      }
      variant.rounds.push({ imported, outcomes });
    }
    const outcomes = variant.rounds.flatMap((round) => round.outcomes);
    variant.medianDocumentEmbeddingMs = median(variant.rounds.map((round) => round.imported.embeddingMs));
    variant.documentsPerSecond = 1000 * documents.length / variant.medianDocumentEmbeddingMs;
    variant.medianWriteMs = median(variant.rounds.map((round) => round.imported.writeMs));
    variant.medianRefreshMs = median(variant.rounds.map((round) => round.imported.refreshMs));
    variant.medianQueryEmbeddingMs = median(outcomes.map((result) => result.queryEmbeddingMs));
    variant.medianSeekdbMs = median(outcomes.map((result) => result.searchMs));
    variant.medianEndToEndMs = median(outcomes.map((result) => result.endToEndMs));
    variant.recallAt3 = outcomes.filter((result) => result.titles.slice(0, 3).includes(result.expectedTitle)).length / outcomes.length;
    run.variants.push(variant);
  }
  report = run;
  $('download').disabled = false;
  status('性能复测完成。可下载各轮实际结果。');
}

$('select').onclick = () => action(selectLibrary);
$('demo').onclick = () => action(() => importIntoLibrary(documents));
$('import').onclick = () => action(async () => {
  const records = [];
  if ($('text').value.trim()) records.push(...splitDocument($('title').value.trim() || 'Untitled', $('text').value));
  for (const file of $('files').files) {
    if (file.size > 128_000) throw new Error('单个文本文件需小于 128 KB。');
    records.push(...splitDocument(file.name.slice(0, 160), await file.text()));
  }
  await importIntoLibrary(records);
});
$('search').onsubmit = (event) => {
  event.preventDefault();
  return action(async () => {
    const { library: name } = context();
    const result = await searchFor($('query').value.trim(), encoder, name);
    $('results').replaceChildren(...result.results.map((item) => {
      const row = document.createElement('li');
      const title = document.createElement('strong');
      const body = document.createElement('p');
      title.textContent = item.title;
      body.textContent = item.text;
      row.append(title, body);
      return row;
    }));
    $('timing').textContent = `查询向量 ${result.queryEmbeddingMs.toFixed(1)} ms · seekdb ${result.searchMs.toFixed(1)} ms · 总计 ${result.endToEndMs.toFixed(1)} ms`;
    status(result.results.length ? `返回 ${result.results.length} 个片段。` : '当前知识库没有匹配结果。');
  });
};
$('benchmark').onclick = () => action(benchmark);
$('download').onclick = () => {
  if (!report) return;
  const link = document.createElement('a');
  link.href = URL.createObjectURL(new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' }));
  link.download = 'pocket-library-benchmark.json';
  link.click();
  setTimeout(() => URL.revokeObjectURL(link.href), 1000);
};
$('library').value = localStorage.getItem('pocket-library') || 'my_library';
void action(selectLibrary);
