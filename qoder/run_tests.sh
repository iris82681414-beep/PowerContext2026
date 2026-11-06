#!/bin/bash
# Test runner script

set -e

echo "=================================="
echo "资料到行动 - 测试运行脚本"
echo "=================================="
echo ""

# Use the specified test interpreter
PYTHON="/Users/liwangsheng/project/oceanbase/.competition/ecosystem/qoder-cn-local/app-venv/bin/python"

# Check if Python interpreter exists
if [ ! -f "$PYTHON" ]; then
    echo "⚠️  指定的 Python 解释器不存在: $PYTHON"
    echo "尝试使用系统 Python..."
    PYTHON="python3"
fi

echo "使用 Python: $PYTHON"
echo "Python 版本: $($PYTHON --version)"
echo ""

# Check if pytest is installed
if ! $PYTHON -m pytest --version > /dev/null 2>&1; then
    echo "❌ pytest 未安装"
    echo "请运行: $PYTHON -m pip install pytest"
    exit 1
fi

echo "✓ pytest 已安装"
echo ""

# Run tests
echo "运行测试..."
echo "=================================="
$PYTHON -m pytest tests/ -v

echo ""
echo "=================================="
echo "测试完成"
echo "=================================="
