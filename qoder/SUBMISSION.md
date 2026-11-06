# Qoder 提测核对入口

- 作品：资料到行动，面向学习和项目工作的资料检索与待办工作台。
- Qoder Sites：https://materials-to-action-xf0r9seqh0p.qoder.zone
- 参赛仓库：https://github.com/iris82681414-beep/PowerContext2026
- 分支：`2026-competition-ecosystem`；作品目录：`qoder/`。
- Qoder CN 个人账号昵称：`nick7829251553`。
- 个人账号页面显示的账号标识：**阿里云账号 ID `1780170667138070`**，供赛事核对个人账号及 Sites 归属。
- 实际主要开发会话：`890f071a-551b-416a-8610-8281599948f4`，Qoder CLI CN 1.1.83。

## 运行与验证

[README](README.md) 包含锁定依赖、官方 seekdb Docker 部署参考、配置示例、初始化、启动和验证步骤。网站提供项目介绍、真实运行截图、源码链接和本地复现入口。实际项目使用 seekdb 1.4 完成项目、资料、引用及待办的存储，并执行中文全文查询；运行时不要求额外的模型账号。

真实数据库验收共 46 项通过，覆盖项目过滤、资料导入、连续原文引用、资料更新提示、状态变更、跨两个独立 HTTP 服务进程恢复及时间一致性。原始证据在 `evidence/integration-acceptance.txt` 和 `evidence/process-restart.json`；网站中的 `assets/app-overview.jpg` 为实际应用截图。

## 开发与发布记录

主要应用代码由上述真实 Qoder 会话生成，源码检查点为 `037bcbf6`。`evidence/qoder-development-events.json` 保留真实工具事件和写入摘要，`evidence/development-provenance.json` 将 16 份主要应用文件与保留检查点逐一对应；其中 11 份与对应的实际 Write 事件逐字节一致。其余文件及后续集成修正的归属见开发记录，不将 Codex 修正归为 Qoder 原样输出。

`evidence/qoder-final-delivery.cast` 是真实 Qoder CLI 最终交付整理环节的终端记录。它与上述主要编码工具事件、源码检查点共同供核对，不作为最初编码全过程的录屏。Sites 由同一个人账号的真实 Qoder 会话完成准备、设为公开并发布。当前网站包含真实运行截图、源码链接、复现步骤及可公开访问的验收证据。

技术记录不包含访问密钥、密码、浏览器会话或模型推理内容。使用效果尚无外部真实用户统计，展示的教学资料和操作记录均标明为演示样例。
