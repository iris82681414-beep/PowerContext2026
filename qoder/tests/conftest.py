"""Test configuration and fixtures."""
import os
import sys
import pytest
import pymysql

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.config import Config
from app.database import init_database, db


class TestConfig(Config):
    """Test configuration."""
    TESTING = True
    DEBUG = True
    SEEKDB_DATABASE = os.getenv('TEST_SEEKDB_DATABASE', 'qoder_test')


@pytest.fixture(scope='session')
def app():
    """Create application for testing."""
    app = create_app(TestConfig)
    return app


@pytest.fixture(scope='session')
def setup_database(app):
    """Set up test database."""
    with app.app_context():
        # Initialize database schema
        init_database()
        yield
        # Cleanup could be added here if needed


@pytest.fixture
def client(app, setup_database):
    """Create test client."""
    with app.test_client() as client:
        with app.app_context():
            yield client


@pytest.fixture
def db_connection(app):
    """Get database connection for direct queries."""
    with app.app_context():
        config = TestConfig.get_db_config()
        conn = pymysql.connect(**config, cursorclass=pymysql.cursors.DictCursor)
        yield conn
        conn.close()


@pytest.fixture(autouse=True)
def clean_database(app, db_connection):
    """Clean database before each test."""
    with app.app_context():
        cursor = db_connection.cursor()
        # Delete in order to respect foreign keys
        cursor.execute("DELETE FROM todos")
        cursor.execute("DELETE FROM documents")
        cursor.execute("DELETE FROM projects")
        db_connection.commit()
        cursor.close()
