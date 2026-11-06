"""Application configuration from environment variables."""
import os
from flask import current_app, has_app_context
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
        values = current_app.config if has_app_context() else vars(cls)
        return {
            'host': values.get('SEEKDB_HOST', cls.SEEKDB_HOST),
            'port': values.get('SEEKDB_PORT', cls.SEEKDB_PORT),
            'user': values.get('SEEKDB_USER', cls.SEEKDB_USER),
            'password': values.get('SEEKDB_PASSWORD', cls.SEEKDB_PASSWORD),
            'database': values.get('SEEKDB_DATABASE', cls.SEEKDB_DATABASE),
            'charset': 'utf8mb4',
            'init_command': "SET time_zone = '+00:00'"
        }
