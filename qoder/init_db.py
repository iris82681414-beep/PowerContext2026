#!/usr/bin/env python3
"""Database initialization script."""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.database import init_database
from app.models.project import Project
from app.models.document import Document


def create_sample_data():
    """Create sample projects and documents for demonstration."""

    # Create sample project
    project = Project.create(
        name="演示项目",
        description="这是一个示例项目，包含三份原创演示资料"
    )

    print(f"创建演示项目: {project['name']} (ID: {project['id']})")

    # Sample document 1: Course notes
    doc1 = Document.create(
        project_id=project['id'],
        title="Python 函数式编程笔记",
        content="""> 原创演示资料，用于体验导入与检索功能。

# Python 函数式编程

## 核心概念

函数式编程是一种编程范式，强调使用函数来解决问题。

### 纯函数
纯函数具有以下特点：
- 相同的输入总是得到相同的输出
- 没有副作用
- 不依赖外部状态

### 高阶函数
高阶函数是指接受函数作为参数或返回函数的函数。

Python 中常见的高阶函数：
- map(): 对序列中每个元素应用函数
- filter(): 过滤序列中的元素
- reduce(): 对序列进行累积计算

### Lambda 表达式
Lambda 是匿名函数的简写形式，适合简单的单行函数。

示例：
```python
square = lambda x: x ** 2
numbers = [1, 2, 3, 4, 5]
squared = list(map(square, numbers))
```

## 应用场景

函数式编程在数据处理、并发编程和测试中有广泛应用。
""",
        source_type="imported",
        source_identifier="课程笔记"
    )

    print(f"导入资料 1: {doc1['title']}")

    # Sample document 2: Experiment record
    doc2 = Document.create(
        project_id=project['id'],
        title="数据库性能测试报告",
        content="""> 原创演示资料：下述数字为虚构教学样例，不是本项目或比赛的实测结果。

# 数据库性能测试报告

## 测试环境

- 数据库: MySQL 8.0
- 服务器: 4核 CPU, 16GB RAM
- 操作系统: Ubuntu 22.04 LTS

## 测试目标

评估不同索引策略对查询性能的影响。

## 测试方案

### 方案一: 无索引
在包含 100 万条记录的表上执行全表扫描。

结果:
- 平均查询时间: 2.3 秒
- CPU 使用率: 85%

### 方案二: B-Tree 索引
为查询字段创建 B-Tree 索引。

结果:
- 平均查询时间: 0.015 秒
- CPU 使用率: 25%
- 性能提升: 153 倍

### 方案三: 全文索引
使用全文索引进行文本搜索。

结果:
- 平均查询时间: 0.045 秒
- 支持中文分词
- 适合文本检索场景

## 结论

1. 索引对查询性能有显著影响
2. B-Tree 索引适合精确查询
3. 全文索引适合文本搜索
4. 应根据查询模式选择合适的索引类型

## 建议

- 定期分析慢查询日志
- 为高频查询字段建立索引
- 避免过度索引影响写入性能
""",
        source_type="imported",
        source_identifier="实验记录"
    )

    print(f"导入资料 2: {doc2['title']}")

    # Sample document 3: Meeting notes
    doc3 = Document.create(
        project_id=project['id'],
        title="项目启动会议纪要",
        content="""> 原创演示资料：人物、会议和任务安排均为示例。

# 项目启动会议纪要

## 会议信息

- 时间: 2026年11月5日 14:00-16:00
- 地点: 会议室 A301
- 参会人员: 张三、李四、王五、赵六

## 会议议程

### 1. 项目背景介绍

张三介绍了项目的背景和目标：
- 开发一个资料检索与待办管理系统
- 支持中文全文搜索
- 提供可追溯的引用功能

### 2. 技术方案讨论

李四提出了技术选型建议：
- 后端: Python + Flask
- 数据库: MySQL + 全文索引
- 前端: HTML + CSS + JavaScript

王五补充了关于 seekdb 的使用说明：
- seekdb 提供增强的全文搜索能力
- 支持中文分词
- 需要配置 ngram 解析器

### 3. 任务分工

经过讨论，确定以下分工：

| 任务 | 负责人 | 截止日期 |
|------|--------|----------|
| 需求分析 | 张三 | 11月10日 |
| 数据库设计 | 李四 | 11月12日 |
| 后端开发 | 王五 | 11月20日 |
| 前端开发 | 赵六 | 11月20日 |
| 测试 | 张三 | 11月25日 |

### 4. 风险识别

团队识别了以下风险：
- 全文搜索性能可能不达标
- 中文分词准确性需要验证
- 开发时间紧张

### 5. 下一步行动

- 各负责人开始详细设计
- 下周三进行进度同步
- 遇到问题及时沟通

## 会议总结

项目正式启动，团队成员明确了各自的任务和时间节点。将采用敏捷开发模式，每周进行进度同步。

记录人: 赵六
审核人: 张三
""",
        source_type="imported",
        source_identifier="会议纪要"
    )

    print(f"导入资料 3: {doc3['title']}")

    print("\n样例数据创建完成！")
    print(f"项目 ID: {project['id']}")
    print(f"资料数量: 3")


if __name__ == '__main__':
    with create_app().app_context():
        print("初始化数据库...")
        init_database()

        print("\n创建样例数据...")
        create_sample_data()

        print("\n数据库初始化完成！")
