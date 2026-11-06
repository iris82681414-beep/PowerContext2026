"""Database connection and operations with full-text search support."""
import pymysql
from contextlib import contextmanager
from flask import g, current_app


class Database:
    """Database manager with full-text search capabilities."""

    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """Initialize database with Flask app."""
        self.app = app
        app.teardown_appcontext(self.close_connection)

    def get_connection(self):
        """Get database connection."""
        if 'db_conn' not in g:
            config = current_app.config
            db_config = {
                'host': config['SEEKDB_HOST'],
                'port': config['SEEKDB_PORT'],
                'user': config['SEEKDB_USER'],
                'password': config['SEEKDB_PASSWORD'],
                'database': config['SEEKDB_DATABASE'],
                'charset': 'utf8mb4',
                'cursorclass': pymysql.cursors.DictCursor
            }
            g.db_conn = pymysql.connect(**db_config)
        return g.db_conn

    def close_connection(self, exception=None):
        """Close database connection."""
        db_conn = g.pop('db_conn', None)
        if db_conn is not None:
            db_conn.close()

    @contextmanager
    def get_cursor(self):
        """Context manager for database cursor."""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()

    def execute(self, query, params=None):
        """Execute a SQL query."""
        with self.get_cursor() as cursor:
            cursor.execute(query, params or ())
            return cursor

    def fetch_one(self, query, params=None):
        """Execute query and fetch one result."""
        with self.get_cursor() as cursor:
            cursor.execute(query, params or ())
            return cursor.fetchone()

    def fetch_all(self, query, params=None):
        """Execute query and fetch all results."""
        with self.get_cursor() as cursor:
            cursor.execute(query, params or ())
            return cursor.fetchall()

    def insert(self, query, params=None):
        """Execute insert query and return last row id."""
        with self.get_cursor() as cursor:
            cursor.execute(query, params or ())
            return cursor.lastrowid


# Global database instance
db = Database()


def init_database():
    """Initialize database schema with full-text indexes."""
    from app.config import Config

    db_config = Config.get_db_config()

    # Create database if not exists
    conn = pymysql.connect(
        host=db_config['host'],
        port=db_config['port'],
        user=db_config['user'],
        password=db_config['password'],
        charset='utf8mb4'
    )

    try:
        with conn.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_config['database']}` "
                          f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        conn.commit()
    finally:
        conn.close()

    # Connect to the database and create tables
    conn = pymysql.connect(**db_config, cursorclass=pymysql.cursors.DictCursor)

    try:
        with conn.cursor() as cursor:
            # Projects table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)

            # Documents table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    project_id INT NOT NULL,
                    title VARCHAR(500) NOT NULL,
                    content LONGTEXT NOT NULL,
                    source_type VARCHAR(50) DEFAULT 'imported',
                    source_identifier VARCHAR(500),
                    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    version INT DEFAULT 1,
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)

            # Todos table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS todos (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    project_id INT NOT NULL,
                    document_id INT,
                    title VARCHAR(500) NOT NULL,
                    description TEXT,
                    quoted_text TEXT,
                    document_summary TEXT,
                    status ENUM('pending', 'in_progress', 'completed') DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    document_version INT,
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE SET NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)

            # Create full-text index with ngram parser for Chinese support
            try:
                cursor.execute("""
                    ALTER TABLE documents ADD FULLTEXT INDEX ft_idx_doc_content
                    (title, content) WITH PARSER ngram
                """)
                print("Created full-text index with ngram parser")
            except pymysql.err.OperationalError as e:
                if e.args[0] == 1061:  # Index already exists
                    print("Full-text index already exists")
                else:
                    raise

        conn.commit()
        print("Database schema initialized successfully")

    finally:
        conn.close()


def search_documents(query, project_id=None, limit=50):
    """
    Search documents using full-text search.

    Args:
        query: Search keyword(s)
        project_id: Optional project filter
        limit: Maximum results

    Returns:
        List of matching documents with highlights
    """
    from app.config import Config

    db_config = Config.get_db_config()
    conn = pymysql.connect(**db_config, cursorclass=pymysql.cursors.DictCursor)

    try:
        with conn.cursor() as cursor:
            # Build full-text search query
            if project_id:
                sql = """
                    SELECT
                        id, project_id, title, content, source_identifier,
                        imported_at, version,
                        MATCH(title, content) AGAINST(%s IN NATURAL LANGUAGE MODE) as relevance
                    FROM documents
                    WHERE project_id = %s
                      AND MATCH(title, content) AGAINST(%s IN NATURAL LANGUAGE MODE)
                    ORDER BY relevance DESC
                    LIMIT %s
                """
                cursor.execute(sql, (query, project_id, query, limit))
            else:
                sql = """
                    SELECT
                        id, project_id, title, content, source_identifier,
                        imported_at, version,
                        MATCH(title, content) AGAINST(%s IN NATURAL LANGUAGE MODE) as relevance
                    FROM documents
                    WHERE MATCH(title, content) AGAINST(%s IN NATURAL LANGUAGE MODE)
                    ORDER BY relevance DESC
                    LIMIT %s
                """
                cursor.execute(sql, (query, query, limit))

            results = cursor.fetchall()

            # Add highlights to results
            for doc in results:
                doc['highlight'] = extract_highlight(doc['content'], query)
                # Truncate content for display
                if len(doc['content']) > 500:
                    doc['content_preview'] = doc['content'][:500] + '...'
                else:
                    doc['content_preview'] = doc['content']

            return results

    finally:
        conn.close()


def extract_highlight(content, query, context_length=100):
    """Extract a highlight snippet from content around the query match."""
    import re

    # Find the first occurrence of query
    pattern = re.compile(re.escape(query), re.IGNORECASE)
    match = pattern.search(content)

    if not match:
        # Return first part of content if no match
        return content[:context_length * 2] + '...' if len(content) > context_length * 2 else content

    start = max(0, match.start() - context_length)
    end = min(len(content), match.end() + context_length)

    snippet = content[start:end]
    if start > 0:
        snippet = '...' + snippet
    if end < len(content):
        snippet = snippet + '...'

    return snippet
