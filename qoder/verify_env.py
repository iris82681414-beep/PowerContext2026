#!/usr/bin/env python3
"""Environment verification script."""
import sys
import os

def check_python_version():
    """Check Python version."""
    print(f"Python version: {sys.version}")
    major, minor = sys.version_info[:2]
    if major >= 3 and minor >= 12:
        print("✓ Python 3.12+ detected")
        return True
    else:
        print("⚠ Python 3.12+ recommended (current: {}.{})".format(major, minor))
        return False

def check_dependencies():
    """Check if required packages are installed."""
    print("\nChecking dependencies...")
    required = ['flask', 'pymysql', 'dotenv', 'pytest']
    missing = []

    for package in required:
        try:
            if package == 'dotenv':
                __import__('dotenv')
            else:
                __import__(package)
            print(f"✓ {package} installed")
        except ImportError:
            print(f"✗ {package} NOT installed")
            missing.append(package)

    if missing:
        print(f"\nInstall missing packages with:")
        print(f"pip install {' '.join(missing)}")
        return False
    return True

def check_database_connection():
    """Check database connection."""
    print("\nChecking database configuration...")

    # Load environment variables
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        print("⚠ python-dotenv not installed, using default config")

    from app.config import Config

    print(f"Database host: {Config.SEEKDB_HOST}")
    print(f"Database port: {Config.SEEKDB_PORT}")
    print(f"Database name: {Config.SEEKDB_DATABASE}")
    print(f"Database user: {Config.SEEKDB_USER}")

    # Check if database name has qoder_ prefix
    if Config.SEEKDB_DATABASE.startswith('qoder_'):
        print("✓ Database name uses qoder_ prefix")
    else:
        print(f"⚠ Database name should use qoder_ prefix (current: {Config.SEEKDB_DATABASE})")

    # Try to connect
    try:
        import pymysql
        conn = pymysql.connect(
            host=Config.SEEKDB_HOST,
            port=Config.SEEKDB_PORT,
            user=Config.SEEKDB_USER,
            password=Config.SEEKDB_PASSWORD,
            charset='utf8mb4'
        )
        print("✓ Database connection successful")
        conn.close()
        return True
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        print("\nPlease check your .env file and ensure MySQL is running")
        return False

def check_file_structure():
    """Check if all required files exist."""
    print("\nChecking file structure...")

    required_files = [
        'app/__init__.py',
        'app/main.py',
        'app/config.py',
        'app/database.py',
        'app/models/project.py',
        'app/models/document.py',
        'app/models/todo.py',
        'app/routes/projects.py',
        'app/routes/documents.py',
        'app/routes/search.py',
        'app/routes/todos.py',
        'templates/index.html',
        'static/css/style.css',
        'static/js/app.js',
        'tests/test_integration.py',
        'init_db.py',
        'requirements.txt',
        '.env.example',
        'README.md'
    ]

    all_exist = True
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✓ {file_path}")
        else:
            print(f"✗ {file_path} MISSING")
            all_exist = False

    return all_exist

def main():
    """Run all checks."""
    print("=" * 60)
    print("资料到行动 - 环境验证脚本")
    print("=" * 60)

    checks = [
        ("Python 版本", check_python_version()),
        ("依赖包", check_dependencies()),
        ("文件结构", check_file_structure()),
        ("数据库连接", check_database_connection())
    ]

    print("\n" + "=" * 60)
    print("验证结果汇总")
    print("=" * 60)

    all_passed = True
    for name, passed in checks:
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"{name}: {status}")
        if not passed:
            all_passed = False

    print("=" * 60)

    if all_passed:
        print("\n✓ 所有检查通过！可以启动应用。")
        print("\n下一步:")
        print("1. 初始化数据库: python init_db.py")
        print("2. 启动应用: python -m app.main")
        print("3. 访问: http://127.0.0.1:5000")
    else:
        print("\n⚠ 部分检查未通过，请根据上述提示进行修复。")

    return 0 if all_passed else 1

if __name__ == '__main__':
    sys.exit(main())
