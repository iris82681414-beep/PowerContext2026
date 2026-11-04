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
