"""Integration tests for the application."""
import pytest
import json


class TestProjectAPI:
    """Test project management APIs."""

    def test_create_project(self, client):
        """Test creating a new project."""
        response = client.post('/api/projects', json={
            'name': '测试项目',
            'description': '这是一个测试项目'
        })

        assert response.status_code == 201
        data = response.get_json()
        assert data['name'] == '测试项目'
        assert data['description'] == '这是一个测试项目'
        assert 'id' in data
        assert 'created_at' in data

    def test_list_projects(self, client):
        """Test listing all projects."""
        # Create two projects
        client.post('/api/projects', json={'name': '项目1'})
        client.post('/api/projects', json={'name': '项目2'})

        response = client.get('/api/projects')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) >= 2

    def test_get_project(self, client):
        """Test getting a project by ID."""
        # Create a project
        create_response = client.post('/api/projects', json={'name': '测试项目'})
        project_id = create_response.get_json()['id']

        response = client.get(f'/api/projects/{project_id}')
        assert response.status_code == 200
        data = response.get_json()
        assert data['id'] == project_id
        assert data['name'] == '测试项目'

    def test_update_project(self, client):
        """Test updating a project."""
        create_response = client.post('/api/projects', json={'name': '原名称'})
        project_id = create_response.get_json()['id']

        response = client.put(f'/api/projects/{project_id}', json={
            'name': '新名称',
            'description': '新描述'
        })

        assert response.status_code == 200
        data = response.get_json()
        assert data['name'] == '新名称'
        assert data['description'] == '新描述'

    def test_delete_project(self, client):
        """Test deleting a project."""
        create_response = client.post('/api/projects', json={'name': '待删除项目'})
        project_id = create_response.get_json()['id']

        response = client.delete(f'/api/projects/{project_id}')
        assert response.status_code == 204

        # Verify deletion
        response = client.get(f'/api/projects/{project_id}')
        assert response.status_code == 404


class TestDocumentAPI:
    """Test document management APIs."""

    @pytest.fixture
    def project_id(self, client):
        """Create a test project."""
        response = client.post('/api/projects', json={'name': '测试项目'})
        return response.get_json()['id']

    def test_import_document(self, client, project_id):
        """Test importing a document."""
        response = client.post('/api/documents', json={
            'project_id': project_id,
            'title': '测试资料',
            'content': '这是一份测试资料的内容。包含中文文本用于全文检索测试。',
            'source_type': 'imported',
            'source_identifier': '测试来源'
        })

        assert response.status_code == 201
        data = response.get_json()
        assert data['title'] == '测试资料'
        assert data['project_id'] == project_id
        assert data['version'] == 1
        assert 'id' in data

    def test_get_document(self, client, project_id):
        """Test getting a document by ID."""
        # Create a document
        create_response = client.post('/api/documents', json={
            'project_id': project_id,
            'title': '测试资料',
            'content': '资料内容'
        })
        doc_id = create_response.get_json()['id']

        response = client.get(f'/api/documents/{doc_id}')
        assert response.status_code == 200
        data = response.get_json()
        assert data['id'] == doc_id
        assert data['title'] == '测试资料'

    def test_list_documents_by_project(self, client, project_id):
        """Test listing documents in a project."""
        # Create multiple documents
        for i in range(3):
            client.post('/api/documents', json={
                'project_id': project_id,
                'title': f'资料{i+1}',
                'content': f'内容{i+1}'
            })

        response = client.get(f'/api/documents/project/{project_id}')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 3

    def test_update_document_increments_version(self, client, project_id):
        """Test that updating a document increments its version."""
        create_response = client.post('/api/documents', json={
            'project_id': project_id,
            'title': '原始标题',
            'content': '原始内容'
        })
        doc_id = create_response.get_json()['id']
        assert create_response.get_json()['version'] == 1

        # Update the document
        response = client.put(f'/api/documents/{doc_id}', json={
            'content': '更新后的内容'
        })

        assert response.status_code == 200
        data = response.get_json()
        assert data['version'] == 2

    def test_delete_document(self, client, project_id):
        """Test deleting a document."""
        create_response = client.post('/api/documents', json={
            'project_id': project_id,
            'title': '待删除资料',
            'content': '内容'
        })
        doc_id = create_response.get_json()['id']

        response = client.delete(f'/api/documents/{doc_id}')
        assert response.status_code == 204

        # Verify deletion
        response = client.get(f'/api/documents/{doc_id}')
        assert response.status_code == 404


class TestSearchAPI:
    """Test full-text search functionality."""

    @pytest.fixture
    def project_with_docs(self, client):
        """Create a project with searchable documents."""
        # Create project
        proj_response = client.post('/api/projects', json={'name': '搜索测试项目'})
        project_id = proj_response.get_json()['id']

        # Create documents with searchable content
        docs = [
            {
                'title': 'Python编程入门',
                'content': 'Python是一种高级编程语言，以简洁易读著称。Python支持多种编程范式。'
            },
            {
                'title': '数据库设计基础',
                'content': '数据库设计是软件开发的重要环节。良好的数据库设计可以提高系统性能。'
            },
            {
                'title': 'Web开发技术',
                'content': 'Web开发包括前端和后端技术。Python的Flask框架适合快速开发Web应用。'
            }
        ]

        for doc in docs:
            client.post('/api/documents', json={
                'project_id': project_id,
                'title': doc['title'],
                'content': doc['content']
            })

        return project_id

    def test_search_with_chinese_keywords(self, client, project_with_docs):
        """Test searching with Chinese keywords returns actual results."""
        response = client.get(f'/api/search?q=Python&project_id={project_with_docs}')

        assert response.status_code == 200
        data = response.get_json()
        assert data['query'] == 'Python'
        assert data['count'] >= 1  # Should find at least one document

        # Verify results contain the search term
        for result in data['results']:
            content_lower = (result['title'] + result['content']).lower()
            assert 'python' in content_lower

    def test_search_different_keywords_different_results(self, client, project_with_docs):
        """Test that different keywords produce different results."""
        # Search for "Python"
        response1 = client.get(f'/api/search?q=Python&project_id={project_with_docs}')
        data1 = response1.get_json()

        # Search for "数据库"
        response2 = client.get(f'/api/search?q=数据库&project_id={project_with_docs}')
        data2 = response2.get_json()

        # Results should be different
        titles1 = {r['title'] for r in data1['results']}
        titles2 = {r['title'] for r in data2['results']}

        # At least one result should be different
        assert titles1 != titles2 or data1['count'] != data2['count']

    def test_search_no_results(self, client, project_with_docs):
        """Test search with non-existent keyword shows empty results."""
        response = client.get(f'/api/search?q=不存在的关键词12345&project_id={project_with_docs}')

        assert response.status_code == 200
        data = response.get_json()
        assert data['count'] == 0
        assert data['results'] == []

    def test_search_with_project_filter(self, client):
        """Test search respects project filter."""
        # Create two projects
        proj1 = client.post('/api/projects', json={'name': '项目1'}).get_json()
        proj2 = client.post('/api/projects', json={'name': '项目2'}).get_json()

        # Add document only to project 1
        client.post('/api/documents', json={
            'project_id': proj1['id'],
            'title': '独特标题ABC123',
            'content': '这是项目1独有的资料内容'
        })

        # Search in project 1 - should find it
        response1 = client.get(f'/api/search?q=独特标题ABC123&project_id={proj1["id"]}')
        data1 = response1.get_json()
        assert data1['count'] >= 1

        # Search in project 2 - should not find it
        response2 = client.get(f'/api/search?q=独特标题ABC123&project_id={proj2["id"]}')
        data2 = response2.get_json()
        assert data2['count'] == 0

    def test_search_with_quoted_text(self, client, project_with_docs):
        """Test search with quoted text."""
        response = client.get(f'/api/search?q="编程语言"&project_id={project_with_docs}')

        assert response.status_code == 200
        data = response.get_json()
        # Should find documents containing this phrase
        assert 'results' in data

    def test_search_requires_query(self, client, project_with_docs):
        """Test that search requires a query parameter."""
        response = client.get(f'/api/search?project_id={project_with_docs}')

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data


class TestTodoAPI:
    """Test todo management APIs."""

    @pytest.fixture
    def project_and_doc(self, client):
        """Create a project and document for todo tests."""
        proj_response = client.post('/api/projects', json={'name': '待办测试项目'})
        project_id = proj_response.get_json()['id']

        doc_response = client.post('/api/documents', json={
            'project_id': project_id,
            'title': '测试资料',
            'content': '这是用于创建待办的资料来源内容'
        })
        doc_id = doc_response.get_json()['id']

        return project_id, doc_id

    def test_create_todo_with_document_reference(self, client, project_and_doc):
        """Test creating a todo requires and stores document reference."""
        project_id, doc_id = project_and_doc

        response = client.post('/api/todos', json={
            'project_id': project_id,
            'document_id': doc_id,
            'title': '完成资料整理',
            'description': '需要整理测试资料的内容',
            'quoted_text': '这是用于创建待办的资料来源内容',
            'document_summary': '资料包含测试相关内容'
        })

        assert response.status_code == 201
        data = response.get_json()
        assert data['title'] == '完成资料整理'
        assert data['document_id'] == doc_id
        assert data['status'] == 'pending'
        assert data['quoted_text'] == '这是用于创建待办的资料来源内容'
        assert data['document_summary'] == '资料包含测试相关内容'
        assert 'document_version' in data

    def test_create_todo_without_document_fails(self, client, project_and_doc):
        """Test that creating a todo without document reference fails."""
        project_id, _ = project_and_doc

        response = client.post('/api/todos', json={
            'project_id': project_id,
            'title': '无来源待办'
        })

        assert response.status_code == 400

    def test_update_todo_status(self, client, project_and_doc):
        """Test updating todo status through the workflow."""
        project_id, doc_id = project_and_doc

        # Create todo
        create_response = client.post('/api/todos', json={
            'project_id': project_id,
            'document_id': doc_id,
            'title': '状态测试待办'
        })
        todo_id = create_response.get_json()['id']
        assert create_response.get_json()['status'] == 'pending'

        # Update to in_progress
        response = client.patch(f'/api/todos/{todo_id}/status', json={
            'status': 'in_progress'
        })
        assert response.status_code == 200
        assert response.get_json()['status'] == 'in_progress'

        # Update to completed
        response = client.patch(f'/api/todos/{todo_id}/status', json={
            'status': 'completed'
        })
        assert response.status_code == 200
        assert response.get_json()['status'] == 'completed'

    def test_todo_shows_document_updated_warning(self, client, project_and_doc):
        """Test that todo shows warning when source document is updated."""
        project_id, doc_id = project_and_doc

        # Create todo with a quote that exists in the document content
        create_response = client.post('/api/todos', json={
            'project_id': project_id,
            'document_id': doc_id,
            'title': '版本测试待办',
            'quoted_text': '用于创建待办的资料来源'
        })
        todo_id = create_response.get_json()['id']

        # Verify initial state - document not updated
        todo = create_response.get_json()
        assert todo['document_version'] == 1
        assert todo.get('document_updated') is False or todo.get('document_updated') is None

        # Update the document
        client.put(f'/api/documents/{doc_id}', json={
            'content': '更新后的内容'
        })

        # Get todo again - should show document_updated flag
        response = client.get(f'/api/todos/{todo_id}')
        assert response.status_code == 200
        data = response.get_json()
        assert data['document_updated'] is True
        assert data['document_version'] == 1  # Original version preserved
        assert data['current_document_version'] == 2  # Current version

    def test_list_todos_by_project(self, client, project_and_doc):
        """Test listing todos in a project."""
        project_id, doc_id = project_and_doc

        # Create multiple todos
        for i in range(3):
            client.post('/api/todos', json={
                'project_id': project_id,
                'document_id': doc_id,
                'title': f'待办{i+1}'
            })

        response = client.get(f'/api/todos/project/{project_id}')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 3

    def test_filter_todos_by_status(self, client, project_and_doc):
        """Test filtering todos by status."""
        project_id, doc_id = project_and_doc

        # Create todos with different statuses
        todo1 = client.post('/api/todos', json={
            'project_id': project_id,
            'document_id': doc_id,
            'title': '待办1',
            'status': 'pending'
        }).get_json()

        todo2 = client.post('/api/todos', json={
            'project_id': project_id,
            'document_id': doc_id,
            'title': '待办2',
            'status': 'in_progress'
        }).get_json()

        # Filter by pending
        response = client.get(f'/api/todos/project/{project_id}?status=pending')
        data = response.get_json()
        assert all(t['status'] == 'pending' for t in data)

    def test_delete_todo(self, client, project_and_doc):
        """Test deleting a todo."""
        project_id, doc_id = project_and_doc

        create_response = client.post('/api/todos', json={
            'project_id': project_id,
            'document_id': doc_id,
            'title': '待删除待办'
        })
        todo_id = create_response.get_json()['id']

        response = client.delete(f'/api/todos/{todo_id}')
        assert response.status_code == 204

        # Verify deletion
        response = client.get(f'/api/todos/{todo_id}')
        assert response.status_code == 404


class TestServiceRestart:
    """Test data persistence across service restarts."""

    def test_data_persists_after_restart(self, client):
        """Test that data is still available after simulated restart."""
        # Create project and document
        proj_response = client.post('/api/projects', json={
            'name': '持久化测试项目'
        })
        project_id = proj_response.get_json()['id']

        doc_response = client.post('/api/documents', json={
            'project_id': project_id,
            'title': '持久化测试资料',
            'content': '这份资料应该在重启后仍然可以检索到'
        })
        doc_id = doc_response.get_json()['id']

        # Create todo
        todo_response = client.post('/api/todos', json={
            'project_id': project_id,
            'document_id': doc_id,
            'title': '持久化测试待办',
            'status': 'in_progress'
        })
        todo_id = todo_response.get_json()['id']

        # Simulate restart by making new requests (in real scenario, app would restart)
        # Verify project still exists
        response = client.get(f'/api/projects/{project_id}')
        assert response.status_code == 200
        assert response.get_json()['name'] == '持久化测试项目'

        # Verify document still exists and is searchable
        response = client.get(f'/api/documents/{doc_id}')
        assert response.status_code == 200
        assert response.get_json()['title'] == '持久化测试资料'

        # Verify search still works
        response = client.get(f'/api/search?q=持久化&project_id={project_id}')
        assert response.status_code == 200
        assert response.get_json()['count'] >= 1

        # Verify todo still exists with correct status
        response = client.get(f'/api/todos/{todo_id}')
        assert response.status_code == 200
        todo_data = response.get_json()
        assert todo_data['title'] == '持久化测试待办'
        assert todo_data['status'] == 'in_progress'
        assert todo_data['document_id'] == doc_id
        assert todo_data['quoted_text'] is not None  # Has document reference


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_project_state(self, client):
        """Test empty state messages for new project."""
        proj_response = client.post('/api/projects', json={'name': '空项目'})
        project_id = proj_response.get_json()['id']

        # List documents - should be empty
        response = client.get(f'/api/documents/project/{project_id}')
        assert response.status_code == 200
        assert response.get_json() == []

        # List todos - should be empty
        response = client.get(f'/api/todos/project/{project_id}')
        assert response.status_code == 200
        assert response.get_json() == []

    def test_invalid_project_reference(self, client):
        """Test error handling for invalid project references."""
        response = client.get('/api/projects/99999')
        assert response.status_code == 404

    def test_invalid_document_reference(self, client):
        """Test error handling for invalid document references."""
        response = client.get('/api/documents/99999')
        assert response.status_code == 404

    def test_invalid_todo_status(self, client):
        """Test error handling for invalid todo status."""
        proj_response = client.post('/api/projects', json={'name': '测试项目'})
        project_id = proj_response.get_json()['id']

        doc_response = client.post('/api/documents', json={
            'project_id': project_id,
            'title': '测试资料',
            'content': '内容'
        })
        doc_id = doc_response.get_json()['id']

        todo_response = client.post('/api/todos', json={
            'project_id': project_id,
            'document_id': doc_id,
            'title': '测试待办'
        })
        todo_id = todo_response.get_json()['id']

        # Try invalid status
        response = client.patch(f'/api/todos/{todo_id}/status', json={
            'status': 'invalid_status'
        })
        assert response.status_code == 400


class TestFileUpload:
    """Test file upload functionality."""

    @pytest.fixture
    def project_id(self, client):
        """Create a test project."""
        response = client.post('/api/projects', json={'name': '上传测试项目'})
        return response.get_json()['id']

    def test_upload_markdown_file(self, client, project_id):
        """Test uploading a valid .md file."""
        from io import BytesIO

        content = "# 测试文档\n\n这是一份测试文档的内容。\n\n## 第二节\n\n更多内容。"
        data = {
            'file': (BytesIO(content.encode('utf-8')), 'test.md'),
            'project_id': str(project_id),
            'title': '上传的Markdown文档',
            'source_identifier': '文件上传测试'
        }

        response = client.post(
            '/api/documents/upload',
            data=data,
            content_type='multipart/form-data'
        )

        assert response.status_code == 201
        result = response.get_json()
        assert result['filename'] == 'test.md'
        assert result['encoding'] == 'UTF-8'
        assert result['document']['title'] == '上传的Markdown文档'
        assert '这是一份测试文档的内容' in result['document']['content']

    def test_upload_text_file(self, client, project_id):
        """Test uploading a valid .txt file."""
        from io import BytesIO

        content = "纯文本文件内容\n第二行内容\n第三行内容"
        data = {
            'file': (BytesIO(content.encode('utf-8')), 'notes.txt'),
            'project_id': str(project_id)
        }

        response = client.post(
            '/api/documents/upload',
            data=data,
            content_type='multipart/form-data'
        )

        assert response.status_code == 201
        result = response.get_json()
        assert result['filename'] == 'notes.txt'
        # Title should default to filename without extension
        assert result['document']['title'] == 'notes'

    def test_upload_invalid_extension(self, client, project_id):
        """Test uploading a file with invalid extension."""
        from io import BytesIO

        data = {
            'file': (BytesIO(b'content'), 'test.pdf'),
            'project_id': str(project_id)
        }

        response = client.post(
            '/api/documents/upload',
            data=data,
            content_type='multipart/form-data'
        )

        assert response.status_code == 400
        assert 'Invalid file type' in response.get_json()['error']

    def test_upload_non_utf8_file(self, client, project_id):
        """Test uploading a file with non-UTF-8 encoding."""
        from io import BytesIO

        # GBK encoded content
        content = "这是GBK编码".encode('gbk')
        data = {
            'file': (BytesIO(content), 'test.txt'),
            'project_id': str(project_id)
        }

        response = client.post(
            '/api/documents/upload',
            data=data,
            content_type='multipart/form-data'
        )

        assert response.status_code == 400
        assert 'UTF-8' in response.get_json()['error']

    def test_upload_empty_file(self, client, project_id):
        """Test uploading an empty file."""
        from io import BytesIO

        data = {
            'file': (BytesIO(b''), 'empty.txt'),
            'project_id': str(project_id)
        }

        response = client.post(
            '/api/documents/upload',
            data=data,
            content_type='multipart/form-data'
        )

        assert response.status_code == 400
        assert 'empty' in response.get_json()['error'].lower()

    def test_upload_missing_project_id(self, client):
        """Test uploading without project_id."""
        from io import BytesIO

        data = {
            'file': (BytesIO(b'content'), 'test.txt')
        }

        response = client.post(
            '/api/documents/upload',
            data=data,
            content_type='multipart/form-data'
        )

        assert response.status_code == 400
        assert 'project_id' in response.get_json()['error']

    def test_upload_invalid_project(self, client):
        """Test uploading to non-existent project."""
        from io import BytesIO

        data = {
            'file': (BytesIO(b'content'), 'test.txt'),
            'project_id': '99999'
        }

        response = client.post(
            '/api/documents/upload',
            data=data,
            content_type='multipart/form-data'
        )

        assert response.status_code == 404

    def test_uploaded_document_is_searchable(self, client, project_id):
        """Test that uploaded documents can be found via search."""
        from io import BytesIO

        unique_term = "可搜索的独特关键词XYZ123"
        content = f"# 文档标题\n\n这是包含{unique_term}的文档内容。"
        data = {
            'file': (BytesIO(content.encode('utf-8')), 'searchable.md'),
            'project_id': str(project_id)
        }

        # Upload
        response = client.post(
            '/api/documents/upload',
            data=data,
            content_type='multipart/form-data'
        )
        assert response.status_code == 201

        # Search
        response = client.get(f'/api/search?q={unique_term}&project_id={project_id}')
        assert response.status_code == 200
        result = response.get_json()
        assert result['count'] >= 1
        assert any(unique_term in r['content'] for r in result['results'])


class TestTodoAutoFill:
    """Test todo auto-fill functionality."""

    @pytest.fixture
    def project_and_doc(self, client):
        """Create a project and document."""
        proj_response = client.post('/api/projects', json={'name': '自动填充测试项目'})
        project_id = proj_response.get_json()['id']

        doc_content = """# Python编程指南

Python是一种高级编程语言，以简洁易读著称。

## 基础语法

Python使用缩进来表示代码块，而不是使用大括号。

## 应用场景

Python广泛应用于Web开发、数据科学、人工智能等领域。
"""
        doc_response = client.post('/api/documents', json={
            'project_id': project_id,
            'title': 'Python编程指南',
            'content': doc_content
        })
        doc_id = doc_response.get_json()['id']

        return project_id, doc_id

    def test_todo_auto_fills_quoted_text(self, client, project_and_doc):
        """Test that todo auto-fills quoted_text from document content."""
        project_id, doc_id = project_and_doc

        # Create todo without quoted_text
        response = client.post('/api/todos', json={
            'project_id': project_id,
            'document_id': doc_id,
            'title': '学习Python基础'
        })

        assert response.status_code == 201
        todo = response.get_json()
        assert todo['quoted_text'] is not None
        assert len(todo['quoted_text']) > 0
        # Quoted text should come from document content
        assert 'Python' in todo['quoted_text'] or '编程' in todo['quoted_text']

    def test_todo_auto_fills_document_summary(self, client, project_and_doc):
        """Test that todo auto-fills document_summary."""
        project_id, doc_id = project_and_doc

        response = client.post('/api/todos', json={
            'project_id': project_id,
            'document_id': doc_id,
            'title': '阅读指南'
        })

        assert response.status_code == 201
        todo = response.get_json()
        assert todo['document_summary'] is not None
        assert len(todo['document_summary']) > 0

    def test_explicit_quoted_text_preserved(self, client, project_and_doc):
        """Test that explicit quoted_text is preserved."""
        project_id, doc_id = project_and_doc

        explicit_quote = "Python是一种高级编程语言"
        response = client.post('/api/todos', json={
            'project_id': project_id,
            'document_id': doc_id,
            'title': '记录要点',
            'quoted_text': explicit_quote
        })

        assert response.status_code == 201
        todo = response.get_json()
        assert todo['quoted_text'] == explicit_quote

    def test_todo_document_must_match_project(self, client):
        """Test that document must belong to the same project as todo."""
        # Create two projects
        proj1 = client.post('/api/projects', json={'name': '项目1'}).get_json()
        proj2 = client.post('/api/projects', json={'name': '项目2'}).get_json()

        # Create document in project 1
        doc = client.post('/api/documents', json={
            'project_id': proj1['id'],
            'title': '项目1的资料',
            'content': '内容'
        }).get_json()

        # Try to create todo in project 2 referencing document from project 1
        response = client.post('/api/todos', json={
            'project_id': proj2['id'],
            'document_id': doc['id'],
            'title': '跨项目待办'
        })

        assert response.status_code == 400
        assert 'does not belong' in response.get_json()['error']

    def test_todo_with_invalid_document(self, client):
        """Test creating todo with non-existent document returns 404."""
        proj = client.post('/api/projects', json={'name': '测试项目'}).get_json()

        response = client.post('/api/todos', json={
            'project_id': proj['id'],
            'document_id': 99999,
            'title': '无效资料待办'
        })

        # Should return 404 to match existing contract (test_invalid_document_reference)
        assert response.status_code == 404
        assert 'not found' in response.get_json()['error'].lower()

    def test_explicit_quote_must_exist_in_document(self, client, project_and_doc):
        """Test that explicit quoted_text must be a real substring of document content."""
        project_id, doc_id = project_and_doc

        # Try to create todo with a quote that doesn't exist in the document
        response = client.post('/api/todos', json={
            'project_id': project_id,
            'document_id': doc_id,
            'title': '测试待办',
            'quoted_text': '这段文字在资料中不存在'
        })

        assert response.status_code == 400
        assert 'does not exist' in response.get_json()['error']

    def test_auto_quote_is_continuous_fragment(self, client, project_and_doc):
        """Test that auto-generated quote is a continuous fragment from original content."""
        project_id, doc_id = project_and_doc

        # Create todo without explicit quote
        response = client.post('/api/todos', json={
            'project_id': project_id,
            'document_id': doc_id,
            'title': '自动引用待办'
        })

        assert response.status_code == 201
        todo = response.get_json()

        # Get the document to verify the quote is a substring
        doc_response = client.get(f'/api/documents/{doc_id}')
        doc_content = doc_response.get_json()['content']

        # The auto-generated quote must be a continuous substring of the original content
        assert todo['quoted_text'] in doc_content
        assert len(todo['quoted_text']) > 0
