"""Todo model operations."""
from app.database import db


class Todo:
    """Todo model for managing action items linked to documents."""

    @staticmethod
    def create(project_id, title, document_id=None, quoted_text=None,
               document_summary=None, description=None, status='pending'):
        """
        Create a new todo.

        Todos must have a document reference to ensure traceability.
        If quoted_text is not provided, it will be auto-filled from the document content.
        The document must belong to the same project as the todo.
        Explicit quoted_text must be a real substring of the document content.
        """
        if document_id is None:
            raise ValueError("Todo must reference a document")

        # Get document and verify it belongs to the same project
        doc_query = "SELECT id, project_id, content, version FROM documents WHERE id = %s"
        doc_result = db.fetch_one(doc_query, (document_id,))

        if not doc_result:
            raise ValueError("Document not found")

        if doc_result['project_id'] != project_id:
            raise ValueError("Document does not belong to the specified project")

        document_version = doc_result['version']
        document_content = doc_result['content']

        # Handle quoted_text
        if not quoted_text or not quoted_text.strip():
            # Auto-fill: extract a real continuous fragment from document content
            quoted_text = Todo._extract_quote_from_content(document_content)
        else:
            # Validate: explicit quote must be a real substring of document content
            if quoted_text not in document_content:
                raise ValueError("Quoted text does not exist in the document content")

        # Auto-fill document_summary if not provided
        if not document_summary or not document_summary.strip():
            document_summary = Todo._extract_summary_from_content(document_content)

        query = """
            INSERT INTO todos (project_id, document_id, title, description,
                             quoted_text, document_summary, status, document_version)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        todo_id = db.insert(query, (
            project_id, document_id, title, description,
            quoted_text, document_summary, status, document_version
        ))
        return Todo.get_by_id(todo_id)

    @staticmethod
    def _extract_quote_from_content(content, max_length=200):
        """Keep quotations as one exact, bounded fragment of the original source."""
        return content.strip()[:max_length] if content else ""

    @staticmethod
    def _extract_summary_from_content(content, max_length=300):
        """Extract a summary from document content."""
        if not content:
            return ""

        # Get first few paragraphs as summary
        paragraphs = content.split('\n\n')
        summary_parts = []
        total_length = 0

        for para in paragraphs:
            para = para.strip()
            if not para or para.startswith('#'):
                continue
            if total_length + len(para) > max_length:
                remaining = max_length - total_length
                if remaining > 50:
                    summary_parts.append(para[:remaining].rsplit(' ', 1)[0] + '...')
                break
            summary_parts.append(para)
            total_length += len(para)

        return ' '.join(summary_parts) if summary_parts else content[:max_length]

    @staticmethod
    def get_by_id(todo_id):
        """Get todo by ID with document information."""
        query = """
            SELECT
                t.*,
                d.title as document_title,
                d.source_identifier,
                d.version as current_document_version,
                p.name as project_name
            FROM todos t
            LEFT JOIN documents d ON t.document_id = d.id
            JOIN projects p ON t.project_id = p.id
            WHERE t.id = %s
        """
        todo = db.fetch_one(query, (todo_id,))

        if todo and todo.get('document_version') is not None:
            todo['document_updated'] = (
                todo['current_document_version'] != todo['document_version']
                if todo['current_document_version'] else False
            )

        return todo

    @staticmethod
    def get_by_project(project_id, status=None):
        """Get all todos in a project, optionally filtered by status."""
        query = """
            SELECT
                t.*,
                d.title as document_title,
                d.source_identifier,
                d.version as current_document_version
            FROM todos t
            LEFT JOIN documents d ON t.document_id = d.id
            WHERE t.project_id = %s
        """
        params = [project_id]

        if status:
            query += " AND t.status = %s"
            params.append(status)

        query += " ORDER BY t.created_at DESC"
        todos = db.fetch_all(query, params)

        for todo in todos:
            if todo.get('document_version') is not None:
                todo['document_updated'] = (
                    todo['current_document_version'] != todo['document_version']
                    if todo['current_document_version'] else False
                )

        return todos

    @staticmethod
    def update_status(todo_id, status):
        """Update todo status."""
        if status not in ['pending', 'in_progress', 'completed']:
            raise ValueError(f"Invalid status: {status}")

        query = "UPDATE todos SET status = %s WHERE id = %s"
        db.execute(query, (status, todo_id))
        return Todo.get_by_id(todo_id)

    @staticmethod
    def update(todo_id, title=None, description=None, status=None):
        """Update todo fields."""
        updates = []
        params = []

        if title is not None:
            updates.append("title = %s")
            params.append(title)
        if description is not None:
            updates.append("description = %s")
            params.append(description)
        if status is not None:
            if status not in ['pending', 'in_progress', 'completed']:
                raise ValueError(f"Invalid status: {status}")
            updates.append("status = %s")
            params.append(status)

        if not updates:
            return Todo.get_by_id(todo_id)

        params.append(todo_id)
        query = f"UPDATE todos SET {', '.join(updates)} WHERE id = %s"
        db.execute(query, params)
        return Todo.get_by_id(todo_id)

    @staticmethod
    def delete(todo_id):
        """Delete a todo."""
        query = "DELETE FROM todos WHERE id = %s"
        db.execute(query, (todo_id,))
        return True

    @staticmethod
    def get_by_document(document_id):
        """Get all todos referencing a document."""
        query = """
            SELECT
                t.*,
                d.title as document_title,
                d.version as current_document_version
            FROM todos t
            LEFT JOIN documents d ON t.document_id = d.id
            WHERE t.document_id = %s
            ORDER BY t.created_at DESC
        """
        todos = db.fetch_all(query, (document_id,))

        for todo in todos:
            if todo.get('document_version') is not None:
                todo['document_updated'] = (
                    todo['current_document_version'] != todo['document_version']
                    if todo['current_document_version'] else False
                )

        return todos
