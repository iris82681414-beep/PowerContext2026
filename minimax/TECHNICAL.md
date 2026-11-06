# MiniMax 工程上下文：续借规则

2026-11-06｜本地及 Linux 验收完成；正式平台得分尚未取得。

## 任务与边界

会员无预约时续借由 14 天改为 21 天；普通读者仍为 14 天，有预约时均为 0 天。函数签名及三项测试不变。原始工程在 `baseline/`，修改后工程在 `fixture/`。

## 上下文模块与技术分工

`sdd.py ingest` 将规格、业务代码和测试导入 seekdb 1.4 的 `engineering_docs` 表，并建立全文索引。`prepare renewal` 按三类来源实际执行 MATCH 查询，返回文件路径、正文、SHA-256 和查询记录；无关盘点资料不被选中。规格副本从 21 天改为 28 天后重新导入，检索返回的新正文与摘要同步更新，随后恢复原规格。

PowerContext 1.2.0 的 builtin runtime 使用 SQLite 保存已完成事项、待办及验证结果，提供记忆版本引用。独立的 `remember` 和 `prepare` 进程读取同一状态库及任务 scope；不依赖恢复完整 Agent 会话。

MiniMax Agent 国内版网页实际接收了上述真实检索资料和已恢复状态，页面模型为 M3.1-Flash。初次余额不足失败，领取账户每日签到积分后重试成功；未购买套餐。模型生成的模块逐字应用到业务文件，生成与应用摘要相同。

## 验证及证据

同三项测试修改前因会员仍返回 14 天而失败一项，普通读者及预约行为通过；修改后本地和 Linux 均三项全通过，测试字节与摘要不变。最新 Linux 验收使用 Python 3.12.3、真实 seekdb 1.4 和锁定依赖，验证了规格更新、修改后源码检索、新完成状态写入，以及两个独立进程恢复相同记忆版本引用。

`evidence/model-web-20261106/validation.json` 关联请求、原始输出、截图、改码差异和测试；`linux-run/summary.json` 记录命令、退出码及源码摘要。模型自述的测试结果不作验收依据。较早失败记录保留；未提交凭据、浏览器会话或模型推理内容。

## 运行入口与限制

按 README 部署数据库、安装 `requirements.lock` 后，执行 `sdd.py ingest`、`prepare renewal` 及 `python -m unittest discover -s fixture -v`。`validate_context.py` 默认使用原始 `baseline/` 重现业务失败及上下文检查，不再次请求模型。新证据目录和专用 sdd_ 数据库用于隔离每轮验证；本地证据不换算为正式比赛分数。
