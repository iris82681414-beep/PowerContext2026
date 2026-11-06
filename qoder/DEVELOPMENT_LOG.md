# 开发记录

## 项目概述

**项目名称**: 资料到行动 - 资料检索与待办工作台

**主要开发工具**: Qoder CN（源码检查点 `037bcbf6`）

**项目基础**: 2026-competition-ecosystem 历史分支

**仓库**: https://github.com/iris82681414-beep/PowerContext2026（分支 2026-competition-ecosystem）

**项目路径**: qoder/

## 需求分析

### 用户问题

课程笔记、实验记录和会议纪要分散，查到一段资料后还要手动记下出处、转成待办，下次打开又不知道进度。

### 核心功能

1. 项目管理和资料导入
2. 中文全文检索（seekdb 1.4 ngram）
3. 可追溯的引用系统（连续真实片段）
4. 待办事项管理
5. 版本追踪和更新提示

## 技术选型

### 后端
- **语言**: Python 3.12
- **框架**: Flask 3.0.0
- **数据库**: seekdb 1.4（端口 2881，兼容 MySQL 协议）
- **全文搜索**: seekdb 1.4 Full-Text Search + ngram 解析器（真实 DDL）

### 前端
- **技术栈**: 原生 HTML + CSS + JavaScript
- **设计理念**: 简洁、响应式、中文友好、无构建依赖

### 测试
- **框架**: pytest 7.4.3
- **覆盖**: 46 项集成测试（含独立进程重启验证）
- **数据库隔离**: TEST_SEEKDB_DATABASE 独立于 SEEKDB_DATABASE

## 架构设计

### 项目结构
```
qoder/
├── app/                    # Flask 应用核心
│   ├── models/            # 数据模型层
│   ├── routes/            # API 路由层
│   ├── config.py          # 配置管理
│   └── database.py        # 数据库操作
├── templates/             # HTML 模板
├── static/               # 静态资源
├── tests/                # 测试文件
├── site/                 # 项目展示网站
└── evidence/             # 验收证据
```

### 数据库设计

#### projects 表
- id: 主键
- name: 项目名称
- description: 项目描述
- created_at, updated_at: 时间戳

#### documents 表
- id: 主键
- project_id: 外键关联项目
- title: 资料标题
- content: 资料内容（LONGTEXT）
- source_type: 来源类型
- source_identifier: 来源标识
- version: 版本号（更新时递增）
- imported_at, updated_at: 时间戳
- **全文索引**: ft_idx_doc_content (title, content) WITH PARSER ngram

#### todos 表
- id: 主键
- project_id: 外键关联项目
- document_id: 外键关联资料（必需）
- title: 待办标题
- description: 待办描述
- quoted_text: 引用文本（必须是原文连续真实片段）
- document_summary: 资料摘要
- status: 状态（pending/in_progress/completed）
- document_version: 创建时的资料版本号
- created_at, updated_at: 时间戳

### API 设计

#### 项目管理
- GET /api/projects - 列出所有项目
- POST /api/projects - 创建项目
- GET /api/projects/<id> - 获取项目详情
- PUT /api/projects/<id> - 更新项目
- DELETE /api/projects/<id> - 删除项目

#### 资料管理
- POST /api/documents - 从 JSON 导入资料
- POST /api/documents/upload - 上传文件（multipart/form-data）
- GET /api/documents/<id> - 获取资料详情
- GET /api/documents/project/<id> - 列出项目资料
- PUT /api/documents/<id> - 更新资料
- DELETE /api/documents/<id> - 删除资料

#### 全文搜索
- GET /api/search?q=<query>&project_id=<id> - 搜索资料

#### 待办管理
- POST /api/todos - 创建待办（自动填充连续真实引用，验证显式引用）
- GET /api/todos/<id> - 获取待办详情
- GET /api/todos/project/<id> - 列出项目待办
- PUT /api/todos/<id> - 更新待办
- PATCH /api/todos/<id>/status - 更新状态
- DELETE /api/todos/<id> - 删除待办

## 实现细节

### 全文搜索实现

使用 seekdb 1.4 的 Full-Text Search 功能，配置 ngram 解析器以支持中文分词。

```sql
ALTER TABLE documents ADD FULLTEXT INDEX ft_idx_doc_content
(title, content) WITH PARSER ngram
```

搜索查询使用自然语言模式：

```sql
SELECT *, MATCH(title, content) AGAINST(%s IN NATURAL LANGUAGE MODE) as relevance
FROM documents
WHERE MATCH(title, content) AGAINST(%s IN NATURAL LANGUAGE MODE)
ORDER BY relevance DESC
```

### 引用完整性保证

1. **自动引用**: `_extract_quote_from_content()` 提取原文的连续真实片段
   - 优先提取第一个有意义的段落
   - 不拼接多段、不添加省略号
   - 保证返回的是原文的真实子串
   - 原文非空时始终返回非空结果

2. **显式引用验证**: 必须验证为 document content 的真实子串
   - 使用 Python `in` 操作符验证
   - 不合法引用返回 ValueError（"Quoted text does not exist in the document content"）
   - API 层捕获并返回 400 错误

3. **版本追踪**:
   - 资料每次更新时，version 字段自动递增
   - 创建待办时，记录当前的 document_version
   - 查询待办时，比较 document_version 和当前 version
   - 如果不一致，设置 document_updated 标志

### 测试库隔离

- `SEEKDB_DATABASE`: 应用数据库（如 `qoder_review_nov6`）
- `TEST_SEEKDB_DATABASE`: 测试数据库（如 `qoder_test`）
- 测试会清空指定测试库下的 projects/documents/todos 表
- fixture 自动初始化指定测试库

## 测试覆盖

### 集成测试（共 46 项）

**测试结果**: 46 项全部通过（真实 seekdb 1.4）

包含：
- 两独立 HTTP 服务进程重启验证
- 真实全文索引 DDL（ngram 解析器）
- 测试库隔离验证

#### 项目管理 (5项)
- 创建、列出、获取、更新、删除项目

#### 资料管理 (5项)
- JSON 导入、文件上传、获取详情、按项目列出、更新（版本号递增）、删除

#### 全文搜索 (6项)
- 中文关键词搜索、不同关键词返回不同结果、空结果处理
- 项目范围过滤、带引号文本搜索、必需查询参数验证

#### 待办管理 (12项)
- 创建带资料引用的待办、自动填充连续真实引用片段
- 显式引用验证（必须是资料中的真实子串）
- 资料与项目匹配验证、状态更新流程
- 资料更新后的版本警告、按项目列出待办
- 不存在的资料返回 404（对齐既有契约）
- 自动引用连续性验证、独立进程重启后数据恢复

#### 文件上传 (8项)
- 上传 .md/.txt 文件、无效扩展名拒绝
- 非 UTF-8 编码拒绝、空文件拒绝
- 缺少 project_id 拒绝、无效项目拒绝、上传后可搜索

#### 边界情况 (3项)
- 空项目状态、无效引用处理、无效状态值处理

#### 独立进程重启 (2项)
- 两独立 HTTP 服务进程间的数据持久化验证
- 真实全文索引 DDL 验证

### 验收证据

- `evidence/integration-acceptance.txt` - 集成验收日志（46 passed）
- `evidence/process-restart.json` - 进程重启验收证据
- `evidence/qoder-development-events.json` - 开发工具事件记录
- `evidence/qoder-final-delivery.cast` - CLI 终端记录

## 演示数据

创建了三个虚构教学示例资料：

1. **Python 函数式编程笔记**（课程笔记）
   - 涵盖纯函数、高阶函数、Lambda 表达式
   - 包含代码示例

2. **数据库性能测试报告**（实验记录）
   - 测试环境、方案、结果
   - 对比不同索引策略
   - 包含性能数据

3. **项目启动会议纪要**（会议纪要）
   - 会议信息、议程、讨论内容
   - 任务分工表格
   - 风险识别和行动计划

所有演示数据明确标注为演示用途，非真实业务数据。重复运行 init_db.py 会追加样例。

## 典型工作流程

1. 创建项目"我的课程"
2. 搜索"函数式"找到 Python 笔记
3. 从原文创建待办，自动填充连续真实引用片段
4. 更新待办状态：未开始 → 进行中 → 完成
5. 重启服务，验证数据和待办仍存在
6. 更新原文，查看待办显示来源已变更警告

## 技术亮点

1. **中文全文搜索**: seekdb 1.4 ngram 解析器，真实 DDL
2. **连续真实引用**: 自动提取原文连续片段，非拼接、非省略
3. **显式引用验证**: 必须是资料内容的真实子串
4. **版本追踪**: 自动记录资料版本，提示引用更新
5. **引用完整性**: 强制待办关联资料来源
6. **参数化 SQL**: 防止 SQL 注入
7. **环境变量配置**: 安全保护数据库凭据
8. **测试库隔离**: TEST_SEEKDB_DATABASE 独立于应用库
9. **独立进程重启**: 两独立 HTTP 服务进程间数据持久化验证

## 已知限制

1. 仅本地回环应用，无账号鉴权
2. 不宣传生产多人服务
3. 前端使用原生 JavaScript，未使用现代框架
4. 未实现资料的文件下载功能

## 后续改进方向（Codex 负责）

1. 集成审查
2. 连续原文引用修正
3. 独立进程测试优化
4. 初始化 app context 优化
5. UTC 连接时区处理
6. 测试库隔离修正

## 分工说明

- **本 Qoder 会话**: 生成主要应用代码（app/、tests/、site/），源码检查点 `037bcbf6`
- **Codex**: 后续进行集成审查、连续原文引用修正、独立进程测试、初始化 app context、UTC 连接时区及测试库隔离修正
- **不冒领他人的修改**

## 总结

本项目完整实现了资料检索与待办管理的核心功能，采用简洁的技术栈，注重数据完整性和用户体验。46 项集成测试全部通过，包含独立进程重启验证和真实全文索引 DDL。演示数据为虚构教学示例，明确标注。

---

**主要开发工具**: Qoder CN
**源码检查点**: 037bcbf6
**完成时间**: 2026年11月
**测试解释器**: /Users/liwangsheng/project/oceanbase/.competition/ecosystem/qoder-cn-local/app-venv/bin/python
**数据库**: seekdb 1.4（端口 2881）
**测试结果**: 46 项全部通过
