# 续借规则的工程上下文

`sdd.py` 把规格、业务代码和测试写入 seekdb。`prepare` 用 seekdb 全文索引逐类查询，把实际来源、内容摘要和 PowerContext 中的任务进展一并交给开发助手。PowerContext 使用本地 SQLite 持久化任务状态，并返回可定位到记忆版本的引用。

## 复现

使用 Python 3.12 和可连接的 seekdb 1.4。在 `minimax/` 安装锁定的依赖：

```sh
uv venv --python 3.12 .venv
uv pip sync --python .venv/bin/python requirements.lock
. .venv/bin/activate
```

设置 `SEEKDB_HOST`、`SEEKDB_PORT`、`SEEKDB_USER` 和 `SEEKDB_PASSWORD`。凭据仅放在本机进程环境中。`ingest` 会替换专用数据库 `sdd_renewal` 中的示例资料，不要使用已有业务数据库。PowerContext 需要 `builtin,client` 可选依赖；只安装基础包会缺少启动模块。

```sh
python sdd.py ingest
python sdd.py prepare renewal
python -m unittest discover -s fixture
python sdd.py remember --done 'Reproduced baseline failure' \
  --next 'Implement member renewal' --verification '14 != 21'
python sdd.py prepare renewal
```

检索应包含 `policy.md`、`loan.py` 和 `test_loan.py`，输出的 `database_queries` 记录实际执行的三类全文查询及返回路径。第二次独立运行 `prepare` 应读到刚保存的进展。基线三项测试中，会员续借返回 14 天，预期为 21 天，测试命令因此预期退出 1；普通读者和已预约情形通过。可将 `fixture/` 复制到临时目录，将副本规格中的 `21-day` 改成 `28-day`，再用 `ingest --root` 导入，检查 `prepare` 返回的新正文与摘要。运行默认 `ingest` 即可还原样例，`--state` 可指定新的记忆文件。

完整复现上述上下文检查（每次使用新的输出目录，并指定允许替换示例资料的专用数据库）：

```sh
python validate_context.py --database sdd_acceptance --output run-evidence/context
```

此命令记录数据库版本、依赖、源码摘要、每一步独立进程的命令和退出码、原始输出及修改前的真实业务失败；还会验证规范更新、恢复原规范和记忆版本引用。它不修改原始业务代码或测试，也不会请求模型。11 月 6 日的真实运行材料在 [evidence/context-20261106](evidence/context-20261106/summary.json)，四项上下文要求已通过，但 `contest_ready`、`minimax_called`、`target_fix_complete` 均为 `false`。技术说明见 [TECHNICAL.md](TECHNICAL.md)。

完整赛题验证还需把 `prepare` 结果交给实际使用 MiniMax 的开发助手，记录代码修改，并对修改后的版本运行上面同一组测试。当前目录保留待修改基线，尚无 MiniMax 实际开发记录或修改后测试结果。

## MiniMax API 补丁入口

也可使用配套入口生成待审阅补丁。将 `MINIMAX_CN_API_KEY` 设置在进程环境中，按下面的命令将真实检索结果交给 MiniMax。国际站使用 `--region global` 和 `MINIMAX_API_KEY`。

```sh
python sdd.py prepare renewal > context.json
python request_patch.py context.json --model "$MINIMAX_MODEL" --output run-evidence/model
```

须先将 `MINIMAX_MODEL` 设置为账号当前可用的 MiniMax 模型，也可直接传入明确的 `--model`；未指定时不会发起请求。输出目录保存请求、响应 ID、模型、用量、内容摘要和 `proposed-loan.py`，不包含 API Key 或模型推理内容。审阅后保留修改前后的源码快照，将提案应用到 `fixture/loan.py`，运行相同且未修改的三项测试并保存日志和代码差异，再通过 `sdd.py remember` 保存验证进展，重新运行 `prepare` 检查状态复用。该入口目前完成命令行校验，实际 API 调用仍待凭据配置。须补齐真实模型改码与修改后通过的证据后，才具备完整提测条件。[MiniMax 官方接口说明](https://platform.minimax.io/docs/api-reference/text-chat-openai)
