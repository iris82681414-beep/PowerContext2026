"""Application configuration from environment variables."""
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Base configuration."""
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-me')
    DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'

    # Database configuration
    SEEKDB_HOST = os.getenv('SEEKDB_HOST', 'localhost')
    SEEKDB_PORT = int(os.getenv('SEEKDB_PORT', '3306'))
    SEEKDB_USER = os.getenv('SEEKDB_USER', 'root')
    SEEKDB_PASSWORD = os.getenv('SEEKDB_PASSWORD', '')
    SEEKDB_DATABASE = os.getenv('SEEKDB_DATABASE', 'qoder_workspace')

    # Server configuration
    HOST = os.getenv('HOST', '127.0.0.1')
    PORT = int(os.getenv('PORT', '5000'))

    @classmethod
    def get_db_config(cls):
        """Return database configuration dict."""
        return {
            'host': cls.SEEKDB_HOST,
            'port': cls.SEEKDB_PORT,
            'user': cls.SEEKDB_USER,
            'password': cls.SEEKDB_PASSWORD,
            'database': cls.SEEKDB_DATABASE,
            'charset': 'utf8mb4'
        }
