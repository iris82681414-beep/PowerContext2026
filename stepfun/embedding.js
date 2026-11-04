import { env, pipeline } from '@huggingface/transformers';

export const MODEL = 'Xenova/all-MiniLM-L6-v2';
export const REVISION = '751bff37182d3f1213fa05d7196b954e230abad9';
env.allowLocalModels = false;
const engines = new Map();

export async function openEncoder(profile, notify = () => {}) {
  const device = profile === 'fp16' ? 'webgpu' : 'wasm';
  if (device === 'webgpu') {
    const adapter = await navigator.gpu?.requestAdapter();
    if (!adapter?.features.has('shader-f16')) throw new Error('WebGPU FP16 unavailable');
  }
  const started = performance.now();
  const cached = engines.has(profile);
  if (!cached) {
    engines.set(profile, pipeline('feature-extraction', MODEL, {
      revision: REVISION, dtype: profile, device,
      progress_callback: (event) => {
        if (event.status === 'progress') notify(`正在加载 ${event.file}，${Math.floor(event.progress)}%`);
      },
    }));
  }
  try {
    const engine = await engines.get(profile);
    const encode = async (texts) => {
      const value = await engine(texts, { pooling: 'mean', normalize: true });
      return value.tolist();
    };
    if (!cached) await encode(['Initialize local embedding inference.']);
    return { profile, device, loadMs: performance.now() - started, cached, encode };
  } catch (error) {
    engines.delete(profile);
    throw error;
  }
}

export async function openDefaultEncoder(notify) {
  try { return await openEncoder('fp16', notify); }
  catch {
    notify('WebGPU FP16 不可用，正在加载 WASM INT8 模型。');
    return openEncoder('q8', notify);
  }
}
