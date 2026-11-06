"""Todo routes."""
from flask import Blueprint, request, jsonify
from app.models.todo import Todo
from app.models.project import Project
from app.models.document import Document

bp = Blueprint('todos', __name__, url_prefix='/api/todos')


@bp.route('', methods=['POST'])
def create_todo():
    """
    Create a new todo.

    Todos must reference a document to ensure traceability.
    """
    data = request.get_json()

    if not data:
        return jsonify({'error': 'Request body is required'}), 400

    required = ['project_id', 'title', 'document_id']
    for field in required:
        if data.get(field) is None:
            return jsonify({'error': f'{field} is required'}), 400

    # Verify project exists
    project = Project.get_by_id(data['project_id'])
    if not project:
        return jsonify({'error': 'Project not found'}), 404

    # Verify document exists
    document = Document.get_by_id(data['document_id'])
    if not document:
        return jsonify({'error': 'Document not found'}), 404

    try:
        todo = Todo.create(
            project_id=data['project_id'],
            title=data['title'],
            document_id=data['document_id'],
            quoted_text=data.get('quoted_text'),
            document_summary=data.get('document_summary'),
            description=data.get('description'),
            status=data.get('status', 'pending')
        )

        return jsonify(todo), 201

    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@bp.route('/<int:todo_id>', methods=['GET'])
def get_todo(todo_id):
    """Get a todo by ID."""
    todo = Todo.get_by_id(todo_id)

    if not todo:
        return jsonify({'error': 'Todo not found'}), 404

    return jsonify(todo)


@bp.route('/project/<int:project_id>', methods=['GET'])
def list_todos(project_id):
    """List all todos in a project."""
    project = Project.get_by_id(project_id)
    if not project:
        return jsonify({'error': 'Project not found'}), 404

    status = request.args.get('status')
    todos = Todo.get_by_project(project_id, status)

    return jsonify(todos)


@bp.route('/<int:todo_id>', methods=['PUT'])
def update_todo(todo_id):
    """Update a todo."""
    todo = Todo.get_by_id(todo_id)

    if not todo:
        return jsonify({'error': 'Todo not found'}), 404

    data = request.get_json()

    try:
        todo = Todo.update(
            todo_id,
            title=data.get('title'),
            description=data.get('description'),
            status=data.get('status')
        )
        return jsonify(todo)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@bp.route('/<int:todo_id>/status', methods=['PATCH'])
def update_todo_status(todo_id):
    """Update only the status of a todo."""
    todo = Todo.get_by_id(todo_id)

    if not todo:
        return jsonify({'error': 'Todo not found'}), 404

    data = request.get_json()
    status = data.get('status')

    if not status:
        return jsonify({'error': 'Status is required'}), 400

    try:
        todo = Todo.update_status(todo_id, status)
        return jsonify(todo)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@bp.route('/<int:todo_id>', methods=['DELETE'])
def delete_todo(todo_id):
    """Delete a todo."""
    todo = Todo.get_by_id(todo_id)

    if not todo:
        return jsonify({'error': 'Todo not found'}), 404

    Todo.delete(todo_id)
    return '', 204


@bp.route('/document/<int:document_id>', methods=['GET'])
def get_todos_by_document(document_id):
    """Get all todos referencing a document."""
    document = Document.get_by_id(document_id)

    if not document:
        return jsonify({'error': 'Document not found'}), 404

    todos = Todo.get_by_document(document_id)
    return jsonify(todos)
