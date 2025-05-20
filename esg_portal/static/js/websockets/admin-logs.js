/**
 * ESG Portal - Admin Logs WebSocket Client
 * 
 * This file provides WebSocket functionality for the admin logs page.
 */

// Variables to store state
let currentLogType = 'user';
let currentPage = 1;
let totalPages = 1;
let logsTableBody = null;
let paginationContainer = null;
let adminSocket = null;

/**
 * Initialize the admin logs WebSocket functionality
 */
function initAdminLogsSocket() {
    // Get the admin socket
    adminSocket = getAdminSocket();
    
    if (!adminSocket) {
        console.error('Admin socket not available');
        return;
    }
    
    // Get DOM elements
    logsTableBody = document.querySelector('#logs-table tbody');
    paginationContainer = document.querySelector('#logs-pagination');
    
    if (!logsTableBody || !paginationContainer) {
        console.error('Required DOM elements not found');
        return;
    }
    
    // Get the current log type from the active tab
    const activeTab = document.querySelector('.nav-link.active');
    if (activeTab) {
        currentLogType = activeTab.getAttribute('data-log-type') || 'user';
    }
    
    // Set up event listeners
    document.addEventListener('adminSocket:connected', () => {
        // Request logs data when connected
        requestLogs(currentLogType, currentPage);
    });
    
    document.addEventListener('adminSocket:logs_data', (event) => {
        // Update the logs table with the received data
        updateLogsTable(event.detail);
    });
    
    // Set up tab click handlers
    const tabs = document.querySelectorAll('[data-log-type]');
    tabs.forEach(tab => {
        tab.addEventListener('click', (e) => {
            e.preventDefault();
            const logType = tab.getAttribute('data-log-type');
            currentLogType = logType;
            currentPage = 1;
            requestLogs(logType, 1);
            
            // Update active tab
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
        });
    });
    
    // If already connected, request logs
    if (isAdminSocketConnected()) {
        requestLogs(currentLogType, currentPage);
    }
}

/**
 * Request logs data from the server
 */
function requestLogs(logType, page) {
    if (!adminSocket) return;
    
    adminSocket.emit('request_logs', {
        type: logType,
        page: page,
        per_page: 50
    });
}

/**
 * Update the logs table with the received data
 */
function updateLogsTable(data) {
    if (!logsTableBody || !data || !data.logs) return;
    
    // Update pagination state
    currentPage = data.page;
    totalPages = data.total_pages;
    
    // Clear the table
    logsTableBody.innerHTML = '';
    
    if (data.logs.length === 0) {
        // No logs to display
        const row = document.createElement('tr');
        row.innerHTML = `
            <td colspan="6" class="text-center">
                <div class="alert alert-info mb-0">
                    <i class="fas fa-info-circle me-2"></i>No logs found.
                </div>
            </td>
        `;
        logsTableBody.appendChild(row);
    } else if (currentLogType === 'user') {
        // User logs
        data.logs.forEach((log, index) => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${log.timestamp}</td>
                <td>
                    ${log.username ? 
                        (log.user_id && log.user_id !== 'anonymous' ? 
                            `<a href="/admin/user/${log.user_id}">${log.username}</a>` : 
                            log.username) : 
                        'Anonymous'}
                </td>
                <td>${log.action}</td>
                <td>
                    ${log.status === 'success' ? 
                        '<span class="badge bg-success">Success</span>' : 
                        '<span class="badge bg-danger">Failure</span>'}
                </td>
                <td>${log.request_path || ''}</td>
                <td>
                    <button class="btn btn-sm btn-outline-primary" type="button" data-bs-toggle="collapse" 
                            data-bs-target="#details${index}" aria-expanded="false" aria-controls="details${index}">
                        <i class="fas fa-info-circle"></i>
                    </button>
                    <div class="collapse mt-2" id="details${index}">
                        <div class="card card-body">
                            <pre class="mb-0" style="white-space: pre-wrap;">${JSON.stringify(log, null, 2)}</pre>
                        </div>
                    </div>
                </td>
            `;
            logsTableBody.appendChild(row);
        });
    } else {
        // Error logs
        data.logs.forEach((log, index) => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td colspan="6">
                    <div class="list-group-item">
                        <pre class="mb-0" style="white-space: pre-wrap;">${log.content}</pre>
                    </div>
                </td>
            `;
            logsTableBody.appendChild(row);
        });
    }
    
    // Update pagination
    updatePagination(data.page, data.total_pages);
}

/**
 * Update the pagination controls
 */
function updatePagination(page, totalPages) {
    if (!paginationContainer) return;
    
    // Clear the pagination container
    paginationContainer.innerHTML = '';
    
    if (totalPages <= 1) {
        // No pagination needed
        return;
    }
    
    const ul = document.createElement('ul');
    ul.className = 'pagination justify-content-center';
    
    // Previous button
    const prevLi = document.createElement('li');
    prevLi.className = `page-item ${page <= 1 ? 'disabled' : ''}`;
    const prevLink = document.createElement('a');
    prevLink.className = 'page-link';
    prevLink.href = '#';
    prevLink.setAttribute('aria-label', 'Previous');
    prevLink.innerHTML = '<span aria-hidden="true">&laquo;</span>';
    if (page > 1) {
        prevLink.addEventListener('click', (e) => {
            e.preventDefault();
            requestLogs(currentLogType, page - 1);
        });
    }
    prevLi.appendChild(prevLink);
    ul.appendChild(prevLi);
    
    // Page numbers
    for (let i = 1; i <= totalPages; i++) {
        // Only show pages near the current page or at the ends
        if (i === 1 || i === totalPages || (i >= page - 1 && i <= page + 1)) {
            const li = document.createElement('li');
            li.className = `page-item ${i === page ? 'active' : ''}`;
            const link = document.createElement('a');
            link.className = 'page-link';
            link.href = '#';
            link.textContent = i;
            if (i !== page) {
                link.addEventListener('click', (e) => {
                    e.preventDefault();
                    requestLogs(currentLogType, i);
                });
            }
            li.appendChild(link);
            ul.appendChild(li);
        } else if (i === 2 || i === totalPages - 1) {
            // Add ellipsis
            const li = document.createElement('li');
            li.className = 'page-item disabled';
            const link = document.createElement('a');
            link.className = 'page-link';
            link.href = '#';
            link.textContent = '...';
            li.appendChild(link);
            ul.appendChild(li);
        }
    }
    
    // Next button
    const nextLi = document.createElement('li');
    nextLi.className = `page-item ${page >= totalPages ? 'disabled' : ''}`;
    const nextLink = document.createElement('a');
    nextLink.className = 'page-link';
    nextLink.href = '#';
    nextLink.setAttribute('aria-label', 'Next');
    nextLink.innerHTML = '<span aria-hidden="true">&raquo;</span>';
    if (page < totalPages) {
        nextLink.addEventListener('click', (e) => {
            e.preventDefault();
            requestLogs(currentLogType, page + 1);
        });
    }
    nextLi.appendChild(nextLink);
    ul.appendChild(nextLi);
    
    paginationContainer.appendChild(ul);
}

// Initialize when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Check if we're on the admin logs page
    if (document.querySelector('#logs-table')) {
        initAdminLogsSocket();
    }
}); 