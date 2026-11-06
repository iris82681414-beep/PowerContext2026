# 资料到行动 - 资料检索与待办工作台

面向学习和项目工作的资料检索与待办管理 Web 应用。

## 功能特点

- **项目管理**: 创建和管理多个项目，组织相关资料
- **资料导入**: 支持 UTF-8 Markdown 和纯文本文件上传，也支持文本粘贴
- **全文检索**: 基于 seekdb 1.4 的中文全文搜索，支持项目范围过滤
- **可追溯引用**: 每个待办必须关联资料来源，自动填充引用文本和摘要
- **版本追踪**: 资料更新时自动提示引用来源已变更
- **待办管理**: 支持未开始、进行中、完成三种状态

## 技术栈

- **后端**: Python 3.12 + Flask 3.0.0
- **数据库**: seekdb 1.4（基于 MySQL 协议，默认端口 2881）
- **全文搜索**: seekdb 1.4 内置 Full-Text Search + ngram 解析器
- **前端**: HTML + CSS + JavaScript（原生）
- **测试**: pytest 7.4.3

## 环境要求

- Python 3.12+
- seekdb 1.4 数据库服务（兼容 MySQL 协议）

## 安装步骤

### 1. 进入项目目录

```bash
cd qoder
```

### 2. 创建虚拟环境

```bash
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置数据库

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
SEEKDB_DATABASE=qoder_review_nov6
```

**说明**:
- 数据库使用 seekdb 1.4，默认端口 2881
- 数据库名称必须使用 `qoder_` 前缀
- 所有配置来自环境变量，代码中不包含任何凭据

### 5. 初始化数据库

```bash
python init_db.py
```

这将创建数据库表结构和三份演示资料。

### 6. 启动应用

```bash
python -m app.main
```

应用将在 `http://127.0.0.1:5000` 启动。

## 使用说明

### 1. 创建项目

点击"新建项目"按钮，输入项目名称和描述。

### 2. 导入资料

支持两种方式：

**方式一：文件上传**
- 点击"上传文件"按钮
- 选择 UTF-8 编码的 .md 或 .txt 文件
- 系统自动验证编码和文件大小（最大 10MB）

**方式二：文本粘贴**
- 在"导入资料"面板填写标题、来源、内容
- 支持 Markdown 格式

### 3. 全文检索

在搜索框输入关键词，系统会：
- 在标题和正文中搜索
- 显示匹配片段高亮
- 支持在当前项目范围内过滤

### 4. 查看原文

点击搜索结果或资料列表中的项目，查看完整原文。

### 5. 创建待办

从资料详情页点击"从此资料创建待办"：
- 待办标题：任务描述
- 引用文本：可手动输入（必须是资料中的真实片段），或自动从资料内容提取
- 资料摘要：可手动输入，或自动生成

**重要**: 
- 每个待办必须关联一份资料，确保可追溯性
- 资料必须属于当前项目
- 显式提供的引用文本必须是资料内容的真实子串，否则返回 400 错误

### 6. 管理待办状态

在待办列表中更改状态：
- 未开始 (pending)
- 进行中 (in_progress)
- 已完成 (completed)

当资料来源更新时，待办会显示警告提示，保留原引用内容供核对。

## 运行测试

### 执行测试

```bash
python -m pytest tests/ -v
```

### 测试覆盖

测试包含以下场景（共 43 项）：
- 资料导入（JSON 和文件上传）
- 不同关键词搜索返回不同结果
- 项目范围过滤
- 空结果处理
- 带引号文本搜索
- 创建带真实来源的待办（自动填充和显式提供）
- 显式引用验证（必须是资料中的真实片段）
- 自动引用验证（必须是资料中的连续片段）
- 资料与项目匹配验证
- 状态更新
- 数据持久化验证
- 原文更新后的引用提示
- 文件上传（编码验证、大小限制、扩展名检查）

### 测试结果

**首轮测试**: 27 通过，1 失败（共 28 项）
- 失败项: test_data_persists_after_restart
- 原因: quoted_text 为 None

**次轮测试**: 40 通过，1 失败（共 41 项）
- 失败项: test_todo_with_invalid_document
- 原因: 期望 400 但应返回 404（与既有契约不一致）

**最新测试**: 43 项（待实际运行验证）
- 修复了待办引用自动填充和验证逻辑
- 对齐了 404 契约
- 新增了显式引用验证和自动引用连续性验证

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
├── init_db.py            # 数据库初始化脚本
├── verify_env.py         # 环境验证脚本
├── requirements.txt      # Python 依赖
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

- `POST /api/todos` - 创建待办（自动填充引用，验证显式引用）
- `GET /api/todos/<id>` - 获取待办详情
- `GET /api/todos/project/<project_id>` - 列出项目待办
- `PUT /api/todos/<id>` - 更新待办
- `PATCH /api/todos/<id>/status` - 更新待办状态
- `DELETE /api/todos/<id>` - 删除待办

## 演示数据

初始化后会创建三份原创演示资料：

1. **Python 函数式编程笔记** - 课程笔记
2. **数据库性能测试报告** - 实验记录
3. **项目启动会议纪要** - 会议纪要

所有演示数据明确标注为演示用途。

## 开发记录

- 基于 2026-competition-ecosystem 历史
- 使用 seekdb 1.4 作为数据库（默认端口 2881）
- 参数化 SQL 防止注入
- 数据库配置完全来自环境变量
- 浏览器不接收数据库凭据
- 首轮测试：27 通过，1 失败
- 次轮测试：40 通过，1 失败
- 最新测试：43 项（待验证）
- 修复内容：待办自动填充引用、显式引用验证、文件上传支持、项目匹配验证

## 项目展示网站

查看 `site/` 目录下的静态展示网站，包含：
- 用户痛点
- 核心功能
- 技术分工
- 运行步骤
- 代码链接
- 验证状态

**注意**: 展示网站为静态页面，不连接数据库。实际应用需按上述步骤启动。

## 许可证

本项目为竞赛参赛作品。
