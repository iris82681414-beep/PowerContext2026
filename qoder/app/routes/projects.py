"""Project routes."""
from flask import Blueprint, request, jsonify
from app.models.project import Project

bp = Blueprint('projects', __name__, url_prefix='/api/projects')


@bp.route('', methods=['GET'])
def list_projects():
    """List all projects."""
    projects = Project.get_all()
    # Add statistics to each project
    for project in projects:
        stats = Project.get_statistics(project['id'])
        project['statistics'] = stats
    return jsonify(projects)


@bp.route('', methods=['POST'])
def create_project():
    """Create a new project."""
    data = request.get_json()

    if not data or not data.get('name'):
        return jsonify({'error': 'Project name is required'}), 400

    project = Project.create(
        name=data['name'],
        description=data.get('description')
    )

    return jsonify(project), 201


@bp.route('/<int:project_id>', methods=['GET'])
def get_project(project_id):
    """Get a project by ID."""
    project = Project.get_by_id(project_id)

    if not project:
        return jsonify({'error': 'Project not found'}), 404

    stats = Project.get_statistics(project_id)
    project['statistics'] = stats

    return jsonify(project)


@bp.route('/<int:project_id>', methods=['PUT'])
def update_project(project_id):
    """Update a project."""
    project = Project.get_by_id(project_id)

    if not project:
        return jsonify({'error': 'Project not found'}), 404

    data = request.get_json()
    project = Project.update(
        project_id,
        name=data.get('name'),
        description=data.get('description')
    )

    return jsonify(project)


@bp.route('/<int:project_id>', methods=['DELETE'])
def delete_project(project_id):
    """Delete a project."""
    project = Project.get_by_id(project_id)

    if not project:
        return jsonify({'error': 'Project not found'}), 404

    Project.delete(project_id)
    return '', 204
