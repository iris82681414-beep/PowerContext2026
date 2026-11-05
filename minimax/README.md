# 续借规则的工程上下文

`sdd.py` 把规格、业务代码和测试写入 seekdb。`prepare` 用 seekdb 全文索引逐类查询，把实际来源、内容摘要和 PowerContext 中的任务进展一并交给开发助手。PowerContext 使用本地 SQLite 持久化任务状态，并返回可定位到记忆版本的引用。

## 复现

使用 Python 3.12 和可连接的 seekdb 1.4。在 `minimax/` 创建虚拟环境并安装 `requirements.txt`。设置 `SEEKDB_HOST`、`SEEKDB_PORT`、`SEEKDB_USER` 和 `SEEKDB_PASSWORD`。`ingest` 会替换专用数据库 `sdd_renewal` 中的示例资料。

```sh
python sdd.py ingest
python sdd.py prepare renewal
python -m unittest discover -s fixture
python sdd.py remember --done 'Reproduced baseline failure' \
  --next 'Implement member renewal' --verification '14 != 21'
python sdd.py prepare renewal
```

检索应包含 `policy.md`、`loan.py` 和 `test_loan.py`，第二次独立运行 `prepare` 应读到刚保存的进展。基线三项测试中，会员续借返回 14 天，预期为 21 天。普通读者和已预约情形通过。可将 `fixture/` 复制到临时目录，将副本规格中的 `21-day` 改成 `28-day`，再用 `ingest --root` 导入，检查 `prepare` 返回的新正文与摘要。运行默认 `ingest` 即可还原样例，`--state` 可指定新的记忆文件。

完整赛题验证还需把 `prepare` 结果交给实际使用 MiniMax 的开发助手，记录代码修改，并对修改后的版本运行上面同一组测试。当前目录保留待修改基线，尚无 MiniMax 实际开发记录或修改后测试结果。

## MiniMax API 补丁入口

也可使用配套入口生成待审阅补丁。将 `MINIMAX_CN_API_KEY` 设置在进程环境中，按下面的命令将真实检索结果交给 MiniMax。国际站使用 `--region global` 和 `MINIMAX_API_KEY`。

```sh
python sdd.py prepare renewal > context.json
python request_patch.py context.json --output run-evidence
```

默认模型为 `MiniMax-M2.5`，可用 `--model` 选择账号支持的 MiniMax 模型。输出目录保存请求、响应 ID、模型、用量和 `proposed-loan.py`。输出不包含 API Key 或模型推理内容。审阅后将提案应用到 `fixture/loan.py`，运行相同的测试并保存日志和代码差异，再通过 `sdd.py remember` 保存验证进展，重新运行 `prepare` 检查状态复用。该入口目前完成命令行校验，实际 API 调用仍待凭据配置。[MiniMax 官方接口说明](https://platform.minimax.io/docs/api-reference/text-chat-openai)
