#!/bin/bash
# Quick start script for the application

set -e

echo "=================================="
echo "资料到行动 - 快速启动脚本"
echo "=================================="
echo ""

# Check Python version
echo "检查 Python 版本..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python 版本: $python_version"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo ""
    echo "创建虚拟环境..."
    python3 -m venv venv
fi

# Activate virtual environment
echo ""
echo "激活虚拟环境..."
source venv/bin/activate

# Install dependencies
echo ""
echo "安装依赖..."
pip install -q -r requirements.txt

# Check if .env exists
if [ ! -f ".env" ]; then
    echo ""
    echo "创建环境变量文件..."
    cp .env.example .env
    echo "⚠️  请编辑 .env 文件，配置数据库连接信息"
    echo ""
    echo "必需的配置项："
    echo "  SEEKDB_HOST=localhost"
    echo "  SEEKDB_PORT=3306"
    echo "  SEEKDB_USER=your_username"
    echo "  SEEKDB_PASSWORD=your_password"
    echo "  SEEKDB_DATABASE=qoder_workspace"
    echo ""
    read -p "配置完成后按回车继续..."
fi

# Run verification
echo ""
echo "运行环境验证..."
python verify_env.py

# Ask to initialize database
echo ""
read -p "是否初始化数据库？(y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "初始化数据库..."
    python init_db.py
fi

# Start application
echo ""
echo "=================================="
echo "启动应用..."
echo "=================================="
echo ""
echo "访问地址: http://127.0.0.1:5000"
echo "按 Ctrl+C 停止服务"
echo ""

python -m app.main
