"""Document model operations."""
from app.database import db, search_documents


class Document:
    """Document model for managing imported materials."""

    @staticmethod
    def create(project_id, title, content, source_type='imported', source_identifier=None):
        """Create a new document."""
        query = """
            INSERT INTO documents (project_id, title, content, source_type, source_identifier)
            VALUES (%s, %s, %s, %s, %s)
        """
        doc_id = db.insert(query, (project_id, title, content, source_type, source_identifier))
        return Document.get_by_id(doc_id)

    @staticmethod
    def get_by_id(doc_id):
        """Get document by ID."""
        query = """
            SELECT d.*, p.name as project_name
            FROM documents d
            JOIN projects p ON d.project_id = p.id
            WHERE d.id = %s
        """
        return db.fetch_one(query, (doc_id,))

    @staticmethod
    def get_by_project(project_id):
        """Get all documents in a project."""
        query = """
            SELECT * FROM documents
            WHERE project_id = %s
            ORDER BY imported_at DESC
        """
        return db.fetch_all(query, (project_id,))

    @staticmethod
    def update(doc_id, title=None, content=None):
        """Update a document and increment version."""
        updates = []
        params = []

        if title is not None:
            updates.append("title = %s")
            params.append(title)
        if content is not None:
            updates.append("content = %s")
            updates.append("version = version + 1")
            params.append(content)

        if not updates:
            return Document.get_by_id(doc_id)

        params.append(doc_id)
        query = f"UPDATE documents SET {', '.join(updates)} WHERE id = %s"
        db.execute(query, params)
        return Document.get_by_id(doc_id)

    @staticmethod
    def delete(doc_id):
        """Delete a document."""
        query = "DELETE FROM documents WHERE id = %s"
        db.execute(query, (doc_id,))
        return True

    @staticmethod
    def search(query, project_id=None, limit=50):
        """
        Search documents using full-text search.

        Args:
            query: Search keywords
            project_id: Optional project filter
            limit: Maximum results

        Returns:
            List of matching documents with highlights
        """
        return search_documents(query, project_id, limit)

    @staticmethod
    def get_version(doc_id):
        """Get current version of a document."""
        query = "SELECT version FROM documents WHERE id = %s"
        result = db.fetch_one(query, (doc_id,))
        return result['version'] if result else None

    @staticmethod
    def check_version(doc_id, expected_version):
        """Check if document version matches expected version."""
        current = Document.get_version(doc_id)
        return current == expected_version if current is not None else None
