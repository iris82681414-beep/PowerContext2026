# 资料到行动 - 资料检索与待办工作台

面向学习和项目工作的资料检索与待办管理 Web 应用。

## 功能特点

- **项目管理**: 创建和管理多个项目，组织相关资料
- **资料导入**: 支持 UTF-8 Markdown 和纯文本文件上传，也支持文本粘贴
- **全文检索**: 基于 seekdb 1.4 的中文全文搜索（ngram 解析器），支持项目范围过滤
- **可追溯引用**: 每个待办必须关联资料来源，自动填充连续真实片段作为引用
- **版本追踪**: 资料更新时自动提示引用来源已变更，保留原引用内容供核对
- **待办管理**: 支持未开始、进行中、完成三种状态

## 技术栈

- **后端**: Python 3.12 + Flask 3.0.0
- **数据库**: seekdb 1.4（基于 MySQL 协议，默认端口 2881）
- **全文搜索**: seekdb 1.4 Full-Text Search + ngram 解析器（真实 DDL）
- **前端**: HTML + CSS + JavaScript（原生，无构建依赖）
- **测试**: pytest 7.4.3（真实数据库验证）

## 环境要求

- Python 3.12+
- seekdb 1.4 数据库服务（兼容 MySQL 协议，端口 2881）

## 安装步骤

### 完整克隆

```bash
git clone https://github.com/iris82681414-beep/PowerContext2026.git
cd PowerContext2026
git checkout 2026-competition-ecosystem
cd qoder
```

### 1. 创建虚拟环境

```bash
python3.12 -m venv venv
source venv/bin/activate  # Linux/macOS
```

### 2. 安装依赖

使用锁定文件确保一致性：

```bash
pip install -r requirements.lock
```

### 3. 配置数据库

已有 seekdb 1.4 时直接填写连接。新 Linux 测试环境可按 [官方 Docker 部署说明](https://github.com/oceanbase/docker-images/blob/main/seekdb/README.md) 启动：

```bash
docker run -d --name qoder-seekdb -p 127.0.0.1:2881:2881 \
  -v qoder-seekdb-data:/var/lib/seekdb \
  oceanbase/seekdb:1.4.0-100000172026082615
```

等待 `mysql -h127.0.0.1 -P2881 -uroot -e 'SELECT VERSION()'` 能连接，再继续。
该默认测试实例使用 root、空密码；将其填入本机 `.env`，不要提交凭据。正式验收使用既有 Linux seekdb 1.4 实例；上述镜像部署命令来自官方说明。

复制环境变量示例文件：

```bash
cp .env.example .env
```

编辑 `.env` 文件，配置 seekdb 连接：

```env
SEEKDB_HOST=localhost
SEEKDB_PORT=2881
SEEKDB_USER=your_username
SEEKDB_PASSWORD=your_password
SEEKDB_DATABASE=qoder_workspace
TEST_SEEKDB_DATABASE=qoder_test
```

**重要说明**:
- 数据库使用 seekdb 1.4，默认端口 2881
- 数据库名称必须使用 `qoder_` 前缀
- `TEST_SEEKDB_DATABASE` 必须是独立的可丢弃测试库（如 `qoder_test`）
- 所有配置来自环境变量，代码中不包含任何凭据

### 4. 初始化数据库

```bash
python init_db.py
```

这将：
- 创建数据库表结构（含 ngram 全文索引 DDL）
- 插入三份虚构教学示例资料（明确标注为演示数据）
- **重复运行会追加样例**，不会覆盖已有数据

### 5. 启动应用

```bash
python -m app.main
```

应用将在 `http://127.0.0.1:5000` 启动（仅本地回环，无账号鉴权）。

## 使用说明

### 典型工作流程

1. **创建项目** → 点击"新建项目"按钮
2. **导入资料** → 文件上传或文本粘贴
3. **全文搜索** → 输入关键词，查看匹配结果
4. **查看原文** → 点击搜索结果查看完整内容
5. **创建待办** → 从资料页创建，自动填充连续真实引用片段
6. **更新进度** → 更改待办状态（未开始→进行中→完成）
7. **验证持久化** → 重启服务后数据仍存在
8. **追踪变更** → 更新原文后，待办显示来源已变更警告

### 导入资料

支持两种方式：

**方式一：文件上传**
- 选择 UTF-8 编码的 .md 或 .txt 文件
- 系统自动验证编码和文件大小（最大 10MB）

**方式二：文本粘贴**
- 在"导入资料"面板填写标题、来源、内容
- 支持 Markdown 格式

### 创建待办

从资料详情页点击"从此资料创建待办"：
- 待办标题：任务描述
- 引用文本：**自动填充为原文的连续真实片段**（非拼接、非省略）
- 资料摘要：自动生成或手动输入

**重要规则**:
- 每个待办必须关联一份资料，确保可追溯性
- 资料必须属于当前项目
- 显式提供的引用文本必须是资料内容的真实子串，否则返回 400 错误
- 自动生成的引用保证是原文的连续片段

## 运行测试

### 执行测试

```bash
python -m pytest tests/ -v
```

### 测试覆盖范围

共 46 项集成测试，覆盖以下具体场景：

**项目管理** (5项)
- 创建、列出、获取、更新、删除项目

**资料管理** (5项)
- JSON 导入、文件上传、获取详情、按项目列出、更新（版本号递增）、删除

**全文搜索** (6项)
- 中文关键词搜索、不同关键词返回不同结果、空结果处理
- 项目范围过滤、带引号文本搜索、必需查询参数验证

**待办管理** (12项)
- 创建带资料引用的待办、自动填充连续真实引用片段
- 显式引用验证（必须是资料中的真实子串）
- 资料与项目匹配验证、状态更新流程
- 资料更新后的版本警告、按项目列出待办
- 不存在的资料返回 404（对齐既有契约）
- 自动引用连续性验证、独立进程重启后数据恢复

**文件上传** (8项)
- 上传 .md/.txt 文件、无效扩展名拒绝
- 非 UTF-8 编码拒绝、空文件拒绝
- 缺少 project_id 拒绝、无效项目拒绝、上传后可搜索

**边界情况** (3项)
- 空项目状态、无效引用处理、无效状态值处理

**独立进程重启** (2项)
- 两独立 HTTP 服务进程间的数据持久化验证
- 真实全文索引 DDL 验证

### 测试结果

**真实 seekdb 1.4 完整测试**: 46 项全部通过

包含：
- 两独立 HTTP 服务进程重启验证
- 真实全文索引 DDL（ngram 解析器）
- 测试库隔离（`qoder_test` 独立于应用库）
- fixture 自动初始化指定测试库

证据文件：
- `evidence/integration-acceptance.txt` - 集成验收日志
- `evidence/process-restart.json` - 进程重启验收证据
- `evidence/qoder-development-events.json` - 开发工具事件记录
- `evidence/qoder-final-delivery.cast` - CLI 终端记录

## 项目结构

```
qoder/
├── app/                    # Flask 应用
│   ├── __init__.py        # 应用工厂
│   ├── main.py            # 入口文件
│   ├── config.py          # 配置管理
│   ├── database.py        # 数据库层（全文搜索）
│   ├── models/            # 数据模型
│   │   ├── project.py
│   │   ├── document.py
│   │   └── todo.py
│   └── routes/            # API 路由
│       ├── projects.py
│       ├── documents.py
│       ├── search.py
│       └── todos.py
├── templates/             # HTML 模板
│   └── index.html
├── static/               # 静态资源
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── app.js
├── tests/                # 测试文件
│   ├── conftest.py
│   └── test_integration.py
├── site/                 # 项目展示网站
│   ├── index.html
│   ├── css/
│   ├── assets/
│   └── README.md
├── evidence/             # 验收证据
│   ├── integration-acceptance.txt
│   ├── process-restart.json
│   ├── qoder-development-events.json
│   └── qoder-final-delivery.cast
├── init_db.py            # 数据库初始化脚本
├── requirements.lock     # 锁定依赖
├── .env.example          # 环境变量示例
└── README.md             # 项目说明
```

## API 端点

### 项目

- `GET /api/projects` - 列出所有项目
- `POST /api/projects` - 创建项目
- `GET /api/projects/<id>` - 获取项目详情
- `PUT /api/projects/<id>` - 更新项目
- `DELETE /api/projects/<id>` - 删除项目

### 资料

- `POST /api/documents` - 从 JSON 导入资料
- `POST /api/documents/upload` - 上传文件（multipart/form-data）
- `GET /api/documents/<id>` - 获取资料详情
- `GET /api/documents/project/<project_id>` - 列出项目资料
- `PUT /api/documents/<id>` - 更新资料
- `DELETE /api/documents/<id>` - 删除资料

### 搜索

- `GET /api/search?q=<query>&project_id=<id>` - 全文搜索

### 待办

- `POST /api/todos` - 创建待办（自动填充连续真实引用，验证显式引用）
- `GET /api/todos/<id>` - 获取待办详情
- `GET /api/todos/project/<project_id>` - 列出项目待办
- `PUT /api/todos/<id>` - 更新待办
- `PATCH /api/todos/<id>/status` - 更新待办状态
- `DELETE /api/todos/<id>` - 删除待办

## 演示数据

初始化后会创建三份**虚构教学示例**资料：

1. **Python 函数式编程笔记** - 课程笔记
2. **数据库性能测试报告** - 实验记录
3. **项目启动会议纪要** - 会议纪要

所有演示数据明确标注为演示用途，非真实业务数据。

## 开发记录

- **主要开发工具**: Qoder CN（源码检查点 `037bcbf6`）
- **项目基础**: 2026-competition-ecosystem 历史分支
- **数据库**: seekdb 1.4（端口 2881，真实 ngram 全文索引 DDL）
- **安全措施**: 参数化 SQL、环境变量配置、浏览器不接收凭据
- **测试验证**: 46 项集成测试全部通过（含独立进程重启）
- **后续工作**: Codex 负责集成审查、连续原文引用修正、测试库隔离修正、UTC 连接时区处理

**分工说明**:
- 本 Qoder 会话生成主要应用代码（app/、tests/、site/）
- Codex 后续进行集成审查和优化
- 不冒领他人的修改

## 项目展示网站

查看 `site/` 目录下的静态展示网站（Qoder Sites 作品）：
- 用户痛点
- 核心功能
- 技术分工
- 运行步骤
- 代码链接
- 真实截图（site/assets/app-overview.jpg）
- 验收证据链接

**注意**:
- 展示网站为静态页面，不连接数据库
- 不是已上线的实时 DB 应用
- 不提供生产多人服务
- 实际应用需按上述步骤本地启动

## 许可证

本项目为竞赛参赛作品。

## 仓库信息

- **GitHub**: https://github.com/iris82681414-beep/PowerContext2026
- **分支**: 2026-competition-ecosystem
- **项目路径**: qoder/
- **源码检查点**: 037bcbf6
