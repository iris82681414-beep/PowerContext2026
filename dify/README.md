# 末班月亮档案室

23:45，夜市的人造月亮不见了。控制室的门禁、机修工单、转运票和温度警报各自只说了一半真相。玩家使用自己的笔记编号逐次调查，拼出「谁拿了工牌」和「为什么移走月亮」两条证据链，再指认嫌疑人。名字猜对也不能跳过调查。结案后可以重开，其他玩家的笔记不受影响。

这是规则推理小游戏。无需模型、Embedding、Rerank 或插件账号。Dify 负责行动分支、整理线索、解锁证据链、检查收集进度、判断指认及展示保存结果；seekdb 负责六份案卷的全文检索，以及每本笔记的线索、尝试次数、结案状态和逐轮记录。配套服务只提供事实读写，不替工作流判断嫌疑人或证据是否充足。

## 环境与部署

使用官方 [Dify 1.10.1](https://github.com/langgenius/dify/tree/1.10.1/docker)、DSL 0.5.0、seekdb 1.4、Docker Compose。配套服务复用 Dify 官方 API 镜像内的 Python 3.12 与 PyMySQL 1.1.2，镜像摘要固定在 `compose.yaml`。也可在 Python 3.12 中安装 `requirements.txt` 独立运行服务。Dify 自身仍使用官方 PostgreSQL/Redis 配置；seekdb 承载的是本游戏数据。

1. 按官方 Docker 部署说明启动 Dify。在本目录复制 `.env.example` 为 `.env`，填写可从 Dify 私有网络访问的 seekdb 地址、端口和数据库账号。将 `ARCHIVE_TOKEN` 换成随机私有令牌，例如用 `python3 -c 'import secrets; print(secrets.token_urlsafe(40))'` 生成；不要提交该文件。令牌只用于私有案卷服务，不是模型密钥。
2. 确认 Dify 的 Docker 网络名，设置 `DIFY_NETWORK`。例如 Dify Compose 项目名为 `ob2026dify` 时，网络为 `ob2026dify_default`；其他部署可通过 `docker network ls` 查看。seekdb 需要能从该网络访问，数据库账号需要在专用库 `dify_night_archive` 中建表和读写的权限。
3. 在本目录初始化并启动服务：

   ```sh
   export DIFY_NETWORK=ob2026dify_default
   docker compose -p night-archive run --rm night-archive init
   docker compose -p night-archive up -d
   ```

   初始化会创建专用库和四张表，写入仓库内的 `case.json` 原创案卷。重复初始化更新案卷，不清空玩家笔记。服务不发布宿主机端口，Dify 通过同一网络内的 `night-archive:8765` 访问。
4. 保留 Dify HTTP 代理的默认访问保护，在其 `ssrf_proxy/squid.conf.template` 的最后一条 `http_access deny all` **之前**添加本服务所需的精确规则，再重启代理：

   ```conf
   acl notebook_archive dstdomain night-archive
   acl notebook_archive_port port 8765
   acl notebook_archive_path urlpath_regex ^/(facts/search|notebook/read|notebook/commit)$
   http_access allow notebook_archive notebook_archive_port notebook_archive_path
   ```

   代理也须接入上述 Dify 网络。不要删除默认拒绝规则。HTTP 仅在私有容器网络中使用；本示例不提供公网服务入口。
5. 在 Dify Studio 导入 `night-archive.yml`，无需修改节点地址或代码。在应用的环境变量中为 Secret 类型的 `ARCHIVE_TOKEN` 填入与 `.env` 相同的值。导入文件里的该值留空是为了不分发真实凭据。
6. 打开该 Workflow 的「预览」，或发布后使用 Dify 生成的应用页面/API。填写笔记编号、行动、关键词。编号为 8–64 位字母、数字、下划线或短横线；相同编号复用同一本笔记。重开时关键词可填「开始」。

## 完整体验样例

以新的笔记编号 `detective_demo_001` 开始，按顺序执行下表。所有状态均保存在 seekdb，工作流多次运行之间不依赖浏览器内存。

| 次序 | 行动 | 输入 | 预期表现 |
| --- | --- | --- | --- |
| 1 | 重开 | 开始 | 线索 0/6、指认 0 次，开始调查 |
| 2 | 指认 | 小扳 | 即使名字正确也提示证据不足，不会结案 |
| 3 | 调查 | 工牌 | 返回 A01、A03，解锁身份链，线索 2/6 |
| 4 | 指认 | 小扳 | 提示仍缺 A04、A06 |
| 5 | 调查 | 冷却台 | 返回 A04、A06，解锁动机链，线索 4/6 |
| 6 | 指认 | 阿栖 | 指认暂未成立，仍在调查中 |
| 7 | 指认 | 小扳 | 结案，引用 A01、A03、A04、A06 解释月亮去向 |
| 8 | 指认 | 小扳 | 已结案，不重复增加指认次数 |
| 9 | 换新编号后指认 | 小扳 | 新笔记线索 0/6，证据不足 |
| 10 | 使用原编号重开 | 开始 | 原笔记线索与尝试次数清空，其他编号不受影响 |
| 11 | 指认 | 小扳 | 重开后再次提示证据不足 |
| 12 | 调查 | 北极企鹅 | 无匹配，提供调查方向，线索仍为 0/6 |

还可以调查「录像」「南门」，寻找两名嫌疑人的排除线索。重复调查不会重复计算已收集的线索。笔记版本号递增，遇到同一本笔记被同时更新时提示重新执行；工作流确认保存成功后才展示进度。

笔记编号用于这款单机示例的进度选择，不提供独立玩家登录或隐私隔离认证。请为不同玩家选择不同编号。每局六份固定原创案卷，无随机生成剧情；目前主要玩法约需 5–10 分钟。数据库或读取服务不可用时工作流会报告节点执行失败，不伪造保存成功；保存接口失败时输出明确的未保存提示。

## 实际运行记录

2026-11-05，使用官方 Dify 1.10.1 容器、其真实代码沙箱和真实 seekdb 1.4 完成验证。导入的就是本目录 DSL 原文，版本 0.5.0，导入状态 `completed`，无版本警告；配置 Secret 环境变量后再核对流程图与原文件完全一致。未更改节点 URL、节点代码或流程图用于测试。

- [完整节点事件与运行 ID](evidence/notebook-workflow-20261105.json)：13 次真实 Workflow 运行，包括上表流程及含引号、反斜线的关键词。每次保留导入信息、`workflow_run_id`、实际节点开始/结束事件、HTTP 返回和最终输出。记录来自实际 SSE 的完整 JSON 事件，访问令牌已替换为 `[REDACTED]`。
- [seekdb 实际读写及重启检查](evidence/notebook-storage-20261105.json)：两本独立笔记与 13 条逐轮记录，并检查案卷服务重启前后记录一致。
- [验证索引与源码摘要](validation-20261105.json)：列出本次验证的源码 SHA-256、运行 ID 和结果，便于核对提交版本。

Dify 图中包含 18 个节点，但每次只执行选中分支的 8 个节点：输入、JSON 编码、行动分支、事实读取、规则判断、进度写入、确认输出、结束。服务名为 `night-archive`，与 DSL 及 Compose 配置一致。数据库凭据仅配置在服务端，工作流不接收数据库密码。

此前四节点无持久化版本及其摘要记录不代表此版；此处证据均来自上述新版的重新导入与执行。游戏、案卷及配套代码为本仓库原创，未复用第三方游戏 DSL。
