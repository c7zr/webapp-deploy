// History Page Handler
document.addEventListener('DOMContentLoaded', async () => {
    await requireAuth();
    initProfileDropdown();
    loadHistory();
    initializeFilters();
});

let currentPage = 1;
let totalPages = 1;
let currentFilters = {
    status: 'all',
    method: 'all',
    search: ''
};

function checkAuth() {
    const token = localStorage.getItem('token') || sessionStorage.getItem('token');
    if (!token) {
        window.location.href = '/login';
        return;
    }
}

function initializeFilters() {
    document.getElementById('applyFilters').addEventListener('click', () => {
        currentFilters.status = document.getElementById('statusFilter').value;
        currentFilters.method = document.getElementById('methodFilter').value;
        currentFilters.search = document.getElementById('searchInput').value.trim();
        currentPage = 1;
        loadHistory();
    });
    
    document.getElementById('clearFilters').addEventListener('click', () => {
        document.getElementById('statusFilter').value = 'all';
        document.getElementById('methodFilter').value = 'all';
        document.getElementById('searchInput').value = '';
        currentFilters = { status: 'all', method: 'all', search: '' };
        currentPage = 1;
        loadHistory();
    });
    
    document.getElementById('prevPage').addEventListener('click', () => {
        if (currentPage > 1) {
            currentPage--;
            loadHistory();
        }
    });
    
    document.getElementById('nextPage').addEventListener('click', () => {
        if (currentPage < totalPages) {
            currentPage++;
            loadHistory();
        }
    });
}

async function loadHistory() {
    try {
        const queryParams = new URLSearchParams({
            page: currentPage,
            limit: 50,
            status: currentFilters.status,
            method: currentFilters.method,
            search: currentFilters.search
        });
        
        const response = await apiCall(`/v2/reports/history?${queryParams}`, {
            method: 'GET'
        });
        
        if (response.ok) {
            const data = await response.json();
            displayHistory(data.reports || []);
            updateStats(data.stats || {});
            updatePagination(data.pagination || {});
        } else {
            displayHistory([]);
        }
    } catch (error) {
        console.error('Error loading history:', error);
        displayHistory([]);
    }
}

function displayHistory(reports) {
    const tbody = document.getElementById('historyTableBody');
    
    if (reports.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" style="text-align: center; color: var(--text-gray); padding: 30px;">
                    No reports found
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = reports.map(report => {
        const statusBadge = report.status === 'success' 
            ? '<span class="status-badge success">Success</span>'
            : '<span class="status-badge failed">Failed</span>';
        
        const date = new Date(report.timestamp).toLocaleString();
        
        return `
            <tr>
                <td>${date}</td>
                <td>${report.target}</td>
                <td>${formatMethod(report.method)}</td>
                <td>${report.type || 'Single'}</td>
                <td>${statusBadge}</td>
                <td>
                    <button class="btn btn-secondary btn-sm" onclick="viewReportDetails('${report.id}')">View</button>
                </td>
            </tr>
        `;
    }).join('');
}

function updateStats(stats) {
    document.getElementById('totalHistoryReports').textContent = stats.total || 0;
    document.getElementById('historySuccess').textContent = stats.successful || 0;
    document.getElementById('historyFailed').textContent = stats.failed || 0;
    
    // Calculate and display success rate
    const total = stats.total || 0;
    const successful = stats.successful || 0;
    const successRate = total > 0 ? Math.round((successful / total) * 100) : 0;
    document.getElementById('successRate').textContent = `${successRate}%`;
}

function updatePagination(pagination) {
    currentPage = pagination.currentPage || 1;
    totalPages = pagination.totalPages || 1;
    
    document.getElementById('pageInfo').textContent = `Page ${currentPage} of ${totalPages}`;
    document.getElementById('prevPage').disabled = currentPage === 1;
    document.getElementById('nextPage').disabled = currentPage === totalPages;
}

function formatMethod(method) {
    const methods = {
        'spam': 'Spam',
        'self_injury': 'Self Injury',
        'violent_threat': 'Violent Threat',
        'hate_speech': 'Hate Speech',
        'nudity': 'Nudity',
        'bullying': 'Bullying',
        'impersonation_me': 'Impersonation (Me)',
        'tmnaofcl': 'TMNAOFCL',
        'sale_illegal': 'Sale of Illegal',
        'violence': 'Violence',
        'intellectual_property': 'IP Violation'
    };
    return methods[method] || method;
}

function viewReportDetails(reportId) {
    alert(`View details for report: ${reportId}\n(Details modal to be implemented)`);
}

function logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    sessionStorage.removeItem('token');
    window.location.href = '/login';
}

