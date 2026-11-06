"""Document routes."""
from flask import Blueprint, request, jsonify
from app.models.document import Document
from app.models.project import Project
import os

bp = Blueprint('documents', __name__, url_prefix='/api/documents')

# File upload constraints
ALLOWED_EXTENSIONS = {'.md', '.txt', '.markdown'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


def allowed_file(filename):
    """Check if file extension is allowed."""
    _, ext = os.path.splitext(filename.lower())
    return ext in ALLOWED_EXTENSIONS


@bp.route('/upload', methods=['POST'])
def upload_document():
    """
    Upload a document file (UTF-8 .md or .txt).

    Form data:
        file: The file to upload
        project_id: Project ID
        title: Document title (optional, defaults to filename)
        source_identifier: Source identifier (optional)
    """
    # Check if file is in request
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    # Validate file extension
    if not allowed_file(file.filename):
        return jsonify({
            'error': f'Invalid file type. Allowed types: {", ".join(ALLOWED_EXTENSIONS)}'
        }), 400

    # Get project_id from form data
    project_id = request.form.get('project_id')
    if not project_id:
        return jsonify({'error': 'project_id is required'}), 400

    try:
        project_id = int(project_id)
    except ValueError:
        return jsonify({'error': 'project_id must be an integer'}), 400

    # Verify project exists
    project = Project.get_by_id(project_id)
    if not project:
        return jsonify({'error': 'Project not found'}), 404

    # Read file content
    try:
        file_content = file.read()

        # Check file size
        if len(file_content) > MAX_FILE_SIZE:
            return jsonify({
                'error': f'File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)}MB'
            }), 400

        # Try to decode as UTF-8
        try:
            content = file_content.decode('utf-8')
        except UnicodeDecodeError as e:
            return jsonify({
                'error': f'File is not valid UTF-8 encoding: {str(e)}'
            }), 400

        # Validate content is not empty
        if not content.strip():
            return jsonify({'error': 'File content is empty'}), 400

    except Exception as e:
        return jsonify({'error': f'Failed to read file: {str(e)}'}), 400

    # Get title (use filename if not provided)
    title = request.form.get('title')
    if not title:
        title = os.path.splitext(file.filename)[0]

    source_identifier = request.form.get('source_identifier', 'file_upload')

    # Create document
    document = Document.create(
        project_id=project_id,
        title=title,
        content=content,
        source_type='file_upload',
        source_identifier=source_identifier
    )

    return jsonify({
        'document': document,
        'filename': file.filename,
        'size': len(file_content),
        'encoding': 'UTF-8'
    }), 201


@bp.route('', methods=['POST'])
def create_document():
    """Import a new document from JSON data."""
    data = request.get_json()

    if not data:
        return jsonify({'error': 'Request body is required'}), 400

    required = ['project_id', 'title', 'content']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f'{field} is required'}), 400

    # Verify project exists
    project = Project.get_by_id(data['project_id'])
    if not project:
        return jsonify({'error': 'Project not found'}), 404

    document = Document.create(
        project_id=data['project_id'],
        title=data['title'],
        content=data['content'],
        source_type=data.get('source_type', 'imported'),
        source_identifier=data.get('source_identifier')
    )

    return jsonify(document), 201


@bp.route('/<int:doc_id>', methods=['GET'])
def get_document(doc_id):
    """Get a document by ID."""
    document = Document.get_by_id(doc_id)

    if not document:
        return jsonify({'error': 'Document not found'}), 404

    return jsonify(document)


@bp.route('/project/<int:project_id>', methods=['GET'])
def list_documents(project_id):
    """List all documents in a project."""
    project = Project.get_by_id(project_id)
    if not project:
        return jsonify({'error': 'Project not found'}), 404

    documents = Document.get_by_project(project_id)
    return jsonify(documents)


@bp.route('/<int:doc_id>', methods=['PUT'])
def update_document(doc_id):
    """Update a document."""
    document = Document.get_by_id(doc_id)

    if not document:
        return jsonify({'error': 'Document not found'}), 404

    data = request.get_json()
    document = Document.update(
        doc_id,
        title=data.get('title'),
        content=data.get('content')
    )

    return jsonify(document)


@bp.route('/<int:doc_id>', methods=['DELETE'])
def delete_document(doc_id):
    """Delete a document."""
    document = Document.get_by_id(doc_id)

    if not document:
        return jsonify({'error': 'Document not found'}), 404

    Document.delete(doc_id)
    return '', 204


@bp.route('/<int:doc_id>/version', methods=['GET'])
def get_document_version(doc_id):
    """Get document version."""
    version = Document.get_version(doc_id)

    if version is None:
        return jsonify({'error': 'Document not found'}), 404

    return jsonify({'id': doc_id, 'version': version})
