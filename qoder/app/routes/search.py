"""Search routes."""
from flask import Blueprint, request, jsonify
from app.models.document import Document
from app.models.project import Project

bp = Blueprint('search', __name__, url_prefix='/api/search')


@bp.route('', methods=['GET'])
def search():
    """
    Search documents using full-text search.

    Query parameters:
        q: Search query (required)
        project_id: Filter by project (optional)
        limit: Maximum results (optional, default 50)
    """
    query = request.args.get('q', '').strip()

    if not query:
        return jsonify({'error': 'Search query is required'}), 400

    project_id = request.args.get('project_id', type=int)
    limit = request.args.get('limit', 50, type=int)

    # Verify project exists if specified
    if project_id:
        project = Project.get_by_id(project_id)
        if not project:
            return jsonify({'error': 'Project not found'}), 404

    results = Document.search(query, project_id, limit)

    return jsonify({
        'query': query,
        'project_id': project_id,
        'count': len(results),
        'results': results
    })


@bp.route('/preview/<int:doc_id>', methods=['GET'])
def search_preview(doc_id):
    """
    Get document preview with search term highlights.

    Query parameters:
        q: Search query to highlight (optional)
    """
    document = Document.get_by_id(doc_id)

    if not document:
        return jsonify({'error': 'Document not found'}), 404

    query = request.args.get('q', '').strip()

    if query:
        from app.database import extract_highlight
        document['highlight'] = extract_highlight(document['content'], query)

    return jsonify(document)
