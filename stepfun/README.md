# 口袋资料库

在浏览器生成文档和查询向量。Node.js 服务使用 seekdb-js 把原文、标题和向量保存在 seekdb。全文与向量召回、融合和排序由 seekdb 执行。

## 启动

需要 Node.js 20 或以上、现代 Chrome 或 Edge，以及一个可访问的 seekdb 1.4 服务。已有 seekdb 服务可直接连接。可在本机用官方镜像启动一个独立示例库。[seekdb 镜像说明](https://github.com/oceanbase/docker-images/blob/main/seekdb/README.md)

```sh
docker run -d --name pocket-seekdb \
  -p 127.0.0.1:2881:2881 \
  -v pocket-seekdb-data:/var/lib/seekdb \
  oceanbase/seekdb:1.4.0-100000172026082615
```

待 seekdb 可接受 SQL 连接后，在 `stepfun/` 执行以下命令。

```sh
npm ci --ignore-scripts
npm run build
npm start
```

打开 `http://127.0.0.1:8787/`。默认连接本机的 `2881` 端口，创建 `stepfun_kb` 数据库。通过进程环境设置 `SEEKDB_HOST`、`SEEKDB_PORT`、`SEEKDB_USER`、`SEEKDB_PASSWORD` 和 `SEEKDB_DATABASE`。数据库配置只用于服务端，创建库需相应权限。服务默认监听本机。

## 验证样例

如需在无外网的浏览器中复测，可在构建前把固定修订的模型配置、分词器和 ONNX 权重放到 `public/models/Xenova/all-MiniLM-L6-v2/`，再运行 `VITE_STEPFUN_LOCAL_WEIGHTS=true npm run build`。本地静态权重仍由浏览器加载和推理。完整对照需要 FP32、INT8 和 FP16 文件。

1. 打开 `my_library`，等界面显示 WebGPU FP16 或 WASM INT8。
2. 点击「导入英文示例」，写入 12 个片段。输入 `How do I let a baked loaf cool before cutting it?` 并检索，核对结果及 `Bread cooling` 的完整原文。
3. 粘贴一段新的资料并导入，例如标题 `Orchid potting`、正文 `Repot an orchid in bark after flowering.`。用 `orchid bark` 查回新增正文。再次导入相同标题和正文，核对片段数量。
4. 将知识库切到 `another_library` 并打开，查询使用新库。切回 `my_library` 后可继续检索先前的资料。
5. 点击「运行三轮对照」，待完成后下载记录。复测使用独立的 `bench_*` 知识库。

## 技术说明

模型是公开的 `Xenova/all-MiniLM-L6-v2`，固定修订 `751bff37182d3f1213fa05d7196b954e230abad9`。Transformers.js 3.8.1 下载公开权重，文档和查询均在浏览器中做均值池化和 L2 归一化，输出 384 维向量。启动时优先探测 `shader-f16` 并执行 WebGPU FP16 探针。若探针失败，则初始化 WASM INT8。每个精度使用自己的集合，保留向量空间的区分。浏览器只下载静态模型和运行时文件。[固定模型文件](https://huggingface.co/Xenova/all-MiniLM-L6-v2/tree/751bff37182d3f1213fa05d7196b954e230abad9/onnx)

| 权重 | 发布文件字节 | FP32 / 当前体积 |
| --- | ---: | ---: |
| FP32 `model.onnx` | 90,387,606 | 1.00 |
| FP16 `model_fp16.onnx` | 45,297,825 | 2.00 |
| INT8 `model_quantized.onnx` | 22,972,370 | 3.93 |

seekdb-js 1.4.0 使用余弦 HNSW 和原文全文索引，调用 `hybridSearch` 让 seekdb 执行融合。后端集合关闭 SDK 内置向量化。批量写入后调用索引刷新，再报告写入结果。标题与正文共同决定片段 ID，重试会更新同一片段。不同知识库及模型精度分开存储。页面保存上次选择的知识库，模型变体变化时可重新导入同一批原文。

复测样例使用 12 篇自编短文和 6 个固定查询。报告记录每轮命中标题、Recall@3、模型加载与缓存状态、向量化吞吐、写入、刷新、seekdb 和端到端延迟。FP32 与 INT8 的单条模式比较精度差异。INT8 的单条和八条模式比较批处理。WebGPU FP16 在支持的浏览器中单独记录。浏览器测量需记录机器及浏览器版本。首次下载与重复使用按原始记录分别解读。

支持 UTF-8 `.txt`、`.md` 或粘贴文本，每次最多 32 个片段。演示模型以英文样例为主。当前真实 seekdb 接口验证覆盖混合检索原文回读、重复导入、刷新后查回新增文档和知识库隔离。端侧性能和浏览器兼容性以实际浏览器复测记录为准。

## 已执行的独立核验

通过 Transformers.js 的 ONNX Runtime 原生 CPU 后端分别加载官方 FP32、INT8 权重。12 篇样例均经本应用写入真实 seekdb，6 条查询均返回预期首条标题和完整原文。两个版本的 Recall@3 和 MRR@5 均为 1.00。该样本用于检查量化后的检索链路，浏览器 WebGPU 和 WASM 的计时与兼容性待独立实测。

2026 年 11 月 5 日，用浏览器分别实际执行 WASM INT8 与 WebGPU FP16。两套集合各保存 12 篇浏览器向量化的样例。检索烘焙问题时，两套集合的首条均为 `Bread cooling`，完整原文与样例一致。浏览器采用本地静态权重，seekdb 经测试连接转发。WebGPU 首次导入在等待数据库应答时达到客户端超时，随后重新打开集合确认已有 12 篇并查回原文。单次端到端时间受连接和冷启动影响。

同一浏览器使用 12 篇、6 问固定样本各跑三轮，原始输出见 `benchmark-20261105.json`。每行包含 18 次查询。

| 后端 | 批大小 | 12 篇向量化中位数 | 端侧吞吐 | Recall@3 |
| --- | ---: | ---: | ---: | ---: |
| WASM FP32 | 1 | 202.7 ms | 59.2 篇/s | 100% |
| WASM INT8 | 1 | 220.5 ms | 54.4 篇/s | 100% |
| WASM INT8 | 8 | 641.1 ms | 18.7 篇/s | 100% |
| WebGPU FP16 | 8 | 26.9 ms | 446.1 篇/s | 100% |

WASM INT8 的权重约为 FP32 的四分之一，在这组短文本上批大小 1 的吞吐约为批大小 8 的 2.91 倍。应用默认 WASM 单条、WebGPU 每批最多 8 条。原始记录把复用已有 INT8 会话与新初始化分开标注，加载字段含读取权重与热身推理。经转发的 seekdb 查询耗时存在波动，应结合原始记录单独查看数据库与端到端结果。
