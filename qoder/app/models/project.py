"""Project model operations."""
from app.database import db


class Project:
    """Project model for managing document collections."""

    @staticmethod
    def create(name, description=None):
        """Create a new project."""
        query = """
            INSERT INTO projects (name, description)
            VALUES (%s, %s)
        """
        project_id = db.insert(query, (name, description))
        return Project.get_by_id(project_id)

    @staticmethod
    def get_by_id(project_id):
        """Get project by ID."""
        query = "SELECT * FROM projects WHERE id = %s"
        return db.fetch_one(query, (project_id,))

    @staticmethod
    def get_all():
        """Get all projects."""
        query = "SELECT * FROM projects ORDER BY created_at DESC"
        return db.fetch_all(query)

    @staticmethod
    def update(project_id, name=None, description=None):
        """Update a project."""
        updates = []
        params = []

        if name is not None:
            updates.append("name = %s")
            params.append(name)
        if description is not None:
            updates.append("description = %s")
            params.append(description)

        if not updates:
            return Project.get_by_id(project_id)

        params.append(project_id)
        query = f"UPDATE projects SET {', '.join(updates)} WHERE id = %s"
        db.execute(query, params)
        return Project.get_by_id(project_id)

    @staticmethod
    def delete(project_id):
        """Delete a project."""
        query = "DELETE FROM projects WHERE id = %s"
        db.execute(query, (project_id,))
        return True

    @staticmethod
    def get_statistics(project_id):
        """Get project statistics."""
        doc_query = "SELECT COUNT(*) as count FROM documents WHERE project_id = %s"
        todo_query = """
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                SUM(CASE WHEN status = 'in_progress' THEN 1 ELSE 0 END) as in_progress,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed
            FROM todos WHERE project_id = %s
        """

        doc_count = db.fetch_one(doc_query, (project_id,))['count']
        todo_stats = db.fetch_one(todo_query, (project_id,))

        return {
            'document_count': doc_count,
            'todo_total': todo_stats['total'],
            'todo_pending': todo_stats['pending'] or 0,
            'todo_in_progress': todo_stats['in_progress'] or 0,
            'todo_completed': todo_stats['completed'] or 0
        }
