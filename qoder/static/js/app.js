// Application state
let currentProjectId = null;
let currentDocumentId = null;

// API helper
async function api(endpoint, method = 'GET', data = null) {
    const options = {
        method,
        headers: {
            'Content-Type': 'application/json'
        }
    };

    if (data) {
        options.body = JSON.stringify(data);
    }

    const response = await fetch(endpoint, options);

    if (response.status === 204) {
        return null;
    }

    const result = await response.json();

    if (!response.ok) {
        throw new Error(result.error || 'Request failed');
    }

    return result;
}

// Notification system
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    document.body.appendChild(notification);

    setTimeout(() => {
        notification.remove();
    }, 3000);
}

// Project management
async function loadProjects() {
    try {
        const projects = await api('/api/projects');
        const select = document.getElementById('current-project');

        select.innerHTML = '<option value="">请选择项目</option>';
        projects.forEach(project => {
            const option = document.createElement('option');
            option.value = project.id;
            option.textContent = `${project.name} (${project.statistics?.document_count || 0} 资料)`;
            select.appendChild(option);
        });

        if (currentProjectId) {
            select.value = currentProjectId;
        }
    } catch (error) {
        showNotification('加载项目失败: ' + error.message, 'error');
    }
}

async function createProject() {
    const name = prompt('输入项目名称:');
    if (!name) return;

    const description = prompt('输入项目描述（可选）:') || '';

    try {
        const project = await api('/api/projects', 'POST', { name, description });
        currentProjectId = project.id;
        await loadProjects();
        document.getElementById('current-project').value = currentProjectId;
        onProjectChange();
        showNotification('项目创建成功', 'success');
    } catch (error) {
        showNotification('创建项目失败: ' + error.message, 'error');
    }
}

async function onProjectChange() {
    const select = document.getElementById('current-project');
    currentProjectId = select.value ? parseInt(select.value) : null;

    if (currentProjectId) {
        await loadDocuments();
        await loadTodos();
    } else {
        document.getElementById('documents-list').innerHTML = '<p class="empty-state">请先选择项目</p>';
        document.getElementById('todos-list').innerHTML = '<p class="empty-state">请先选择项目</p>';
    }
}

// Document management
async function loadDocuments() {
    if (!currentProjectId) return;

    try {
        const documents = await api(`/api/documents/project/${currentProjectId}`);
        const container = document.getElementById('documents-list');

        if (documents.length === 0) {
            container.innerHTML = '<p class="empty-state">暂无资料，请先导入</p>';
            return;
        }

        container.innerHTML = documents.map(doc => `
            <div class="list-item" onclick="viewDocument(${doc.id})">
                <h3>${escapeHtml(doc.title)}</h3>
                <div class="result-meta">
                    <span>来源: ${escapeHtml(doc.source_identifier || '未标注')}</span> |
                    <span>导入时间: ${formatDate(doc.imported_at)}</span> |
                    <span>版本: ${doc.version}</span>
                </div>
            </div>
        `).join('');
    } catch (error) {
        showNotification('加载资料失败: ' + error.message, 'error');
    }
}

async function importDocument(event) {
    event.preventDefault();

    if (!currentProjectId) {
        showNotification('请先选择项目', 'error');
        return;
    }

    const title = document.getElementById('doc-title').value;
    const source = document.getElementById('doc-source').value;
    const content = document.getElementById('doc-content').value;

    try {
        await api('/api/documents', 'POST', {
            project_id: currentProjectId,
            title,
            content,
            source_type: 'imported',
            source_identifier: source || '未标注'
        });

        document.getElementById('import-form').reset();
        await loadDocuments();
        showNotification('资料导入成功', 'success');
    } catch (error) {
        showNotification('导入失败: ' + error.message, 'error');
    }
}

async function uploadDocument(event) {
    event.preventDefault();

    if (!currentProjectId) {
        showNotification('请先选择项目', 'error');
        return;
    }

    const fileInput = document.getElementById('file-input');
    const file = fileInput.files[0];

    if (!file) {
        showNotification('请选择文件', 'error');
        return;
    }

    const title = document.getElementById('upload-title').value;
    const source = document.getElementById('upload-source').value;

    const formData = new FormData();
    formData.append('file', file);
    formData.append('project_id', currentProjectId);
    if (title) formData.append('title', title);
    if (source) formData.append('source_identifier', source);

    try {
        const response = await fetch('/api/documents/upload', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || 'Upload failed');
        }

        document.getElementById('upload-form').reset();
        await loadDocuments();
        showNotification(`文件上传成功: ${result.filename} (${result.size} bytes)`, 'success');
    } catch (error) {
        showNotification('上传失败: ' + error.message, 'error');
    }
}

function switchTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.tab === tabName) {
            btn.classList.add('active');
        }
    });

    // Update tab content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    document.getElementById(`${tabName}-tab`).classList.add('active');
}

async function viewDocument(docId) {
    try {
        const doc = await api(`/api/documents/${docId}`);
        currentDocumentId = docId;

        document.getElementById('modal-title').textContent = doc.title;
        document.getElementById('modal-source').textContent = `来源: ${doc.source_identifier || '未标注'}`;
        document.getElementById('modal-date').textContent = `导入时间: ${formatDate(doc.imported_at)}`;
        document.getElementById('modal-content').textContent = doc.content;

        document.getElementById('document-modal').classList.add('active');
    } catch (error) {
        showNotification('加载资料详情失败: ' + error.message, 'error');
    }
}

// Search functionality
async function performSearch() {
    const query = document.getElementById('search-input').value.trim();

    if (!query) {
        showNotification('请输入搜索关键词', 'error');
        return;
    }

    if (!currentProjectId) {
        showNotification('请先选择项目', 'error');
        return;
    }

    try {
        const result = await api(`/api/search?q=${encodeURIComponent(query)}&project_id=${currentProjectId}`);
        const container = document.getElementById('search-results');

        if (result.count === 0) {
            container.innerHTML = '<p class="empty-state">未找到匹配的资料</p>';
            return;
        }

        container.innerHTML = `
            <p style="margin-bottom: 15px; color: #7f8c8d;">找到 ${result.count} 条结果</p>
            ${result.results.map(doc => `
                <div class="result-item" onclick="viewDocument(${doc.id})">
                    <h3>${escapeHtml(doc.title)}</h3>
                    <div class="result-meta">
                        <span>来源: ${escapeHtml(doc.source_identifier || '未标注')}</span> |
                        <span>导入时间: ${formatDate(doc.imported_at)}</span>
                    </div>
                    <div class="result-highlight">${escapeHtml(doc.highlight || doc.content_preview || '')}</div>
                </div>
            `).join('')}
        `;
    } catch (error) {
        showNotification('搜索失败: ' + error.message, 'error');
    }
}

// Todo management
async function loadTodos() {
    if (!currentProjectId) return;

    try {
        const todos = await api(`/api/todos/project/${currentProjectId}`);
        const container = document.getElementById('todos-list');

        if (todos.length === 0) {
            container.innerHTML = '<p class="empty-state">暂无待办</p>';
            return;
        }

        container.innerHTML = todos.map(todo => `
            <div class="todo-item status-${todo.status}">
                <div class="todo-header">
                    <span class="todo-title">${escapeHtml(todo.title)}</span>
                    <span class="todo-status">${getStatusText(todo.status)}</span>
                </div>
                <div class="todo-source">
                    来源: ${escapeHtml(todo.document_title || '未知')} (${escapeHtml(todo.source_identifier || '未标注')})
                </div>
                ${todo.quoted_text ? `
                    <div class="todo-quoted">
                        <strong>引用:</strong> ${escapeHtml(todo.quoted_text)}
                    </div>
                ` : ''}
                ${todo.document_summary ? `
                    <div style="font-size: 0.9em; color: #555; margin-top: 8px;">
                        <strong>摘要:</strong> ${escapeHtml(todo.document_summary)}
                    </div>
                ` : ''}
                ${todo.document_updated ? `
                    <div class="todo-warning">
                        ⚠️ 资料来源已更新（当前版本: ${todo.current_document_version}, 引用版本: ${todo.document_version}）
                    </div>
                ` : ''}
                <div class="todo-actions">
                    <select onchange="updateTodoStatus(${todo.id}, this.value)" ${todo.status === 'completed' ? 'disabled' : ''}>
                        <option value="pending" ${todo.status === 'pending' ? 'selected' : ''}>未开始</option>
                        <option value="in_progress" ${todo.status === 'in_progress' ? 'selected' : ''}>进行中</option>
                        <option value="completed" ${todo.status === 'completed' ? 'selected' : ''}>已完成</option>
                    </select>
                    <button class="btn btn-danger" onclick="deleteTodo(${todo.id})">删除</button>
                </div>
            </div>
        `).join('');
    } catch (error) {
        showNotification('加载待办失败: ' + error.message, 'error');
    }
}

function showCreateTodoModal() {
    if (!currentDocumentId) {
        showNotification('请先选择资料', 'error');
        return;
    }

    document.getElementById('todo-document-id').value = currentDocumentId;
    document.getElementById('todo-modal').classList.add('active');
}

async function createTodo(event) {
    event.preventDefault();

    if (!currentProjectId) {
        showNotification('请先选择项目', 'error');
        return;
    }

    const documentId = parseInt(document.getElementById('todo-document-id').value);
    const title = document.getElementById('todo-title').value;
    const description = document.getElementById('todo-description').value;
    const quotedText = document.getElementById('todo-quoted-text').value;
    const summary = document.getElementById('todo-summary').value;

    try {
        await api('/api/todos', 'POST', {
            project_id: currentProjectId,
            document_id: documentId,
            title,
            description,
            quoted_text: quotedText,
            document_summary: summary
        });

        document.getElementById('todo-form').reset();
        document.getElementById('todo-modal').classList.remove('active');
        await loadTodos();
        showNotification('待办创建成功', 'success');
    } catch (error) {
        showNotification('创建待办失败: ' + error.message, 'error');
    }
}

async function updateTodoStatus(todoId, status) {
    try {
        await api(`/api/todos/${todoId}/status`, 'PATCH', { status });
        await loadTodos();
        showNotification('状态更新成功', 'success');
    } catch (error) {
        showNotification('更新状态失败: ' + error.message, 'error');
        await loadTodos();
    }
}

async function deleteTodo(todoId) {
    if (!confirm('确定要删除这个待办吗？')) return;

    try {
        await api(`/api/todos/${todoId}`, 'DELETE');
        await loadTodos();
        showNotification('待办已删除', 'success');
    } catch (error) {
        showNotification('删除失败: ' + error.message, 'error');
    }
}

// Utility functions
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDate(dateString) {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function getStatusText(status) {
    const statusMap = {
        'pending': '未开始',
        'in_progress': '进行中',
        'completed': '已完成'
    };
    return statusMap[status] || status;
}

// Event listeners
document.addEventListener('DOMContentLoaded', () => {
    // Project management
    document.getElementById('new-project-btn').addEventListener('click', createProject);
    document.getElementById('current-project').addEventListener('change', onProjectChange);

    // Document import (paste tab)
    document.getElementById('import-form').addEventListener('submit', importDocument);

    // Document upload (upload tab)
    document.getElementById('upload-form').addEventListener('submit', uploadDocument);

    // Tab switching
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            switchTab(btn.dataset.tab);
        });
    });

    // Search
    document.getElementById('search-btn').addEventListener('click', performSearch);
    document.getElementById('search-input').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            performSearch();
        }
    });

    // Modal close buttons
    document.querySelectorAll('.modal .close').forEach(btn => {
        btn.addEventListener('click', function() {
            this.closest('.modal').classList.remove('active');
        });
    });

    // Create todo from document modal
    document.getElementById('create-todo-btn').addEventListener('click', showCreateTodoModal);

    // Todo form submission
    document.getElementById('todo-form').addEventListener('submit', createTodo);

    // Close modal when clicking outside
    window.addEventListener('click', (e) => {
        if (e.target.classList.contains('modal')) {
            e.target.classList.remove('active');
        }
    });

    // Load initial data
    loadProjects();
});
