# 续借规则的工程上下文

`sdd.py` 把规格、业务代码和测试写入 seekdb。`prepare` 用 seekdb 全文索引逐类查询，把实际来源、内容摘要和 PowerContext 中的任务进展一并交给开发助手。PowerContext 使用本地 SQLite 持久化任务状态，并返回可定位到记忆版本的引用。

11 月 6 日已通过官方 MiniMax Agent 国内版、页面选择的 **M3.1-Flash** 完成真实改码。会员无预约时返回 21 天，普通读者仍为 14 天，有预约时均为 0 天。模型原始输出已逐字应用到 `fixture/loan.py`；同一份三项测试修改前为一项预期失败，修改后全部通过。真实 seekdb 1.4 的 Linux 运行还验证了修改后代码检索及 PowerContext 跨独立进程恢复。[请求、原始代码、差异、截图和完整验收](evidence/model-web-20261106/validation.json)。这些是交付证据，尚非平台正式得分。

提交用 [一页技术说明（PDF）](output/pdf/technical-note.pdf)，同内容的可编辑版本在 [TECHNICAL.md](TECHNICAL.md)。

## 复现

克隆参赛仓库并进入对应目录：

```sh
git clone --branch 2026-competition-ecosystem https://github.com/iris82681414-beep/PowerContext2026.git
cd PowerContext2026/minimax
```

使用 Python 3.12 和可连接的 seekdb 1.4。已有数据库可直接配置连接；新的 Linux 测试环境可按 [官方 Docker 部署说明](https://github.com/oceanbase/docker-images/blob/main/seekdb/README.md) 启动仅监听本机的实例：

```sh
docker run -d --name minimax-seekdb -p 127.0.0.1:2881:2881 \
  -v minimax-seekdb-data:/var/lib/seekdb \
  oceanbase/seekdb:1.4.0-100000172026082615
```

等待 `mysql -h127.0.0.1 -P2881 -uroot -e 'SELECT VERSION()'` 成功。该默认测试实例使用 root、空密码；连接账号需能创建专用数据库和全文索引。正式验收使用的是既有 Linux seekdb 1.4 实例，上述镜像命令为新环境复现参考。

在 `minimax/` 用 Python 标准虚拟环境安装锁定依赖，不要求预装 uv：

```sh
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.lock
```

设置 `SEEKDB_HOST`、`SEEKDB_PORT`、`SEEKDB_USER` 和 `SEEKDB_PASSWORD`。凭据仅放在本机进程环境中。`ingest` 会替换专用数据库 `sdd_renewal` 中的示例资料，不要使用已有业务数据库。PowerContext 需要 `builtin,client` 可选依赖；只安装基础包会缺少启动模块。

```sh
python sdd.py ingest
python sdd.py prepare renewal
python -m unittest discover -s fixture
python sdd.py remember --done 'Applied MiniMax member renewal change' \
  --next 'Review the validated delivery' --verification 'Same 3 tests pass'
python sdd.py prepare renewal
```

检索应包含 `policy.md`、`loan.py` 和 `test_loan.py`，输出的 `database_queries` 记录实际执行的三类全文查询及返回路径。第二次独立运行 `prepare` 应读到刚保存的进展。当前 `fixture/` 是修改后的业务工程，三项测试预期退出 0；`baseline/` 保留原始工程，会员续借返回 14 天，预期 21 天，测试预期退出 1，普通读者和预约行为通过。两处 `test_loan.py` 的字节和摘要相同。可用 `python -m unittest discover -s baseline -v` 重现缺口；模型改码差异见 `evidence/model-web-20261106/change.diff`。

完整复现上述上下文检查（每次使用新的输出目录，并指定允许替换示例资料的专用数据库）：

```sh
python validate_context.py --database sdd_acceptance --output run-evidence/context
```

此命令默认导入 `baseline/`（可用 `--root` 指定另一份原始工程），记录数据库版本、依赖、源码摘要、独立进程命令及原始输出；验证真实业务失败、规范更新、恢复和记忆版本引用。它不修改业务代码或测试，也不会再次请求模型，因此自己的模型调用状态仍为 `false`。它完成后默认数据库保存的是基线资料；运行 `sdd.py --database sdd_acceptance ingest` 可导入当前修改后工程。较早的上下文运行保留在 [evidence/context-20261106](evidence/context-20261106/summary.json)，完整模型改码验收在 [最新 Linux 验收](evidence/model-web-20261106/linux-run/summary.json)。技术说明见 [TECHNICAL.md](TECHNICAL.md)。

同日较早在 Linux x86_64、Python 3.12.3 的新虚拟环境按相同锁文件完成上下文验证，连接真实 seekdb 1.4；[当时的 Linux 原始证据](evidence/context-linux-20261106/summary.json)记录了当时的源码摘要、依赖下载与离线安装日志。为避免镜像同步延迟，镜像缺少的 `pydantic==2.14.3`、`pydantic-core==2.50.4` 从 PyPI 补齐，依赖版本没有变更。后续模型修改及验证入口调整由最新验收中的源码摘要单独记录，没有覆盖历史证据。

实际使用方式为官方 MiniMax Agent 网页附件输入，账户每日签到免费积分支持了这次请求，没有购买套餐或创建 API Key。模型读取 `request.txt` 中来自真实 seekdb 的规格、代码和测试，以及 PowerContext 恢复的状态，生成完整模块。原始输出在 `generated-loan.py`，与实际应用文件的摘要一致。测试结果由本地及 Linux 命令独立执行；模型回答中自述“测试通过”不作为验证依据。最终 Linux 日志还记录了新完成状态写入、重新导入修改后源码，以及两个独立 `prepare` 进程读取相同的记忆引用和新源码。

## MiniMax API 补丁入口

也可使用配套入口生成待审阅补丁。将 `MINIMAX_CN_API_KEY` 设置在进程环境中，按下面的命令将真实检索结果交给 MiniMax。国际站使用 `--region global` 和 `MINIMAX_API_KEY`。

```sh
python sdd.py prepare renewal > context.json
python request_patch.py context.json --model "$MINIMAX_MODEL" --output run-evidence/model
```

须先将 `MINIMAX_MODEL` 设置为账号当前可用的 MiniMax 模型，也可直接传入明确的 `--model`；未指定时不会发起请求。输出目录保存请求、响应 ID、模型、用量、内容摘要和 `proposed-loan.py`，不包含 API Key 或模型推理内容。此 API 入口仅完成命令行校验，本次实际成功使用的是上述官方网页入口。接入后须实际应用代码、保留相同测试及运行记录，并通过 `sdd.py remember` 和独立 `prepare` 验证进度复用；本次完整记录以上述网页请求及最新 Linux 验收为准。[MiniMax 官方接口说明](https://platform.minimax.io/docs/api-reference/text-chat-openai)
