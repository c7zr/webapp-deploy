// Admin Dashboard Handler
let currentReportsPage = 1;
let totalReportsPages = 1;

document.addEventListener('DOMContentLoaded', async () => {
    await requireAuth();
    initProfileDropdown();
    checkAdminRole();
    loadAdminStats();
    initializeTabs();
    loadUsers();
});

function checkAuth() {
    if (!token) {
        window.location.href = '/login';
        return;
    }
}

function checkAdminRole() {
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    if (user.role !== 'admin' && user.role !== 'owner') {
        alert('Access denied. Admin privileges required.');
        window.location.href = '/dashboard';
        return;
    }
}

function initializeTabs() {
    const tabs = document.querySelectorAll('.tab-btn');
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const targetTab = tab.dataset.tab;
            switchTab(targetTab);
        });
    });
    
    // Initialize forms and buttons
    const addUserBtn = document.getElementById('addUserBtn');
    const exportReportsBtn = document.getElementById('exportReports');
    const systemConfigForm = document.getElementById('systemConfigForm');
    const clearLogsBtn = document.getElementById('clearLogs');
    const userSearchInput = document.getElementById('userSearch');
    const blacklistAddForm = document.getElementById('blacklistAddForm');
    const blacklistSearchInput = document.getElementById('blacklistSearch');
    const userEditForm = document.getElementById('userEditForm');
    
    if (addUserBtn) addUserBtn.addEventListener('click', showAddUserModal);
    if (exportReportsBtn) exportReportsBtn.addEventListener('click', exportReports);
    
    // Pagination controls for reports
    const prevReportsBtn = document.getElementById('prevReportsPage');
    const nextReportsBtn = document.getElementById('nextReportsPage');
    if (prevReportsBtn) prevReportsBtn.addEventListener('click', () => {
        if (currentReportsPage > 1) {
            currentReportsPage--;
            loadAllReports();
        }
    });
    if (nextReportsBtn) nextReportsBtn.addEventListener('click', () => {
        if (currentReportsPage < totalReportsPages) {
            currentReportsPage++;
            loadAllReports();
        }
    });
    if (systemConfigForm) systemConfigForm.addEventListener('submit', saveSystemConfig);
    if (clearLogsBtn) clearLogsBtn.addEventListener('click', clearSystemLogs);
    if (userSearchInput) userSearchInput.addEventListener('input', filterUsers);
    
    // addBlacklistBtn uses onclick attribute in HTML, no need for event listener here
    
    if (blacklistAddForm) blacklistAddForm.addEventListener('submit', addToBlacklist);
    if (blacklistSearchInput) blacklistSearchInput.addEventListener('input', filterBlacklist);
    if (userEditForm) userEditForm.addEventListener('submit', saveUserChanges);
    
    // Modal close
    document.querySelectorAll('.close, .close-modal').forEach(el => {
        el.addEventListener('click', closeModal);
    });
    
    // Click outside modal to close
    window.addEventListener('click', (e) => {
        if (e.target.classList.contains('modal')) {
            closeModal();
        }
    });
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
    document.querySelectorAll('.admin-tab-content').forEach(content => {
        content.classList.remove('active');
    });
    
    const targetContent = document.getElementById(`${tabName}Tab`);
    if (targetContent) {
        targetContent.classList.add('active');
        
        // Load data for the specific tab
        if (tabName === 'users') {
            loadUsers();
        } else if (tabName === 'pending') {
            loadPendingAccounts();
        } else if (tabName === 'reports') {
            loadAllReports();
        } else if (tabName === 'blacklist') {
            loadBlacklist();
        } else if (tabName === 'system') {
            loadSystemConfig();
        } else if (tabName === 'logs') {
            loadSystemLogs();
        }
    }
}

async function loadAdminStats() {
    try {
        const response = await apiCall('/v2/admin/stats', {
            method: 'GET'
        });
        
        if (response.ok) {
            const data = await response.json();
            document.getElementById('totalUsers').textContent = data.totalUsers || 0;
            document.getElementById('totalSystemReports').textContent = data.totalReports || 0;
            document.getElementById('systemSuccessRate').textContent = (data.successRate || 0) + '%';
            document.getElementById('activeUsers').textContent = data.activeToday || 0;
        }
    } catch (error) {
        console.error('Error loading admin stats:', error);
    }
}

async function loadUsers() {
    try {
        const response = await apiCall('/v2/admin/users', {
            method: 'GET'
        });
        
        if (response.ok) {
            const data = await response.json();
            displayUsers(data.users || []);
        }
    } catch (error) {
        console.error('Error loading users:', error);
        displayUsers([]);
    }
}

function displayUsers(users) {
    const tbody = document.getElementById('usersTableBody');
    
    if (users.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="8" style="text-align: center; padding: 30px;">No users found</td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = users.map(user => {
        const roleBadge = getRoleBadge(user.role);
        const statusBadge = user.isActive 
            ? '<span class="status-badge success">Active</span>'
            : '<span class="status-badge failed">Inactive</span>';
        const registered = new Date(user.createdAt).toLocaleDateString();
        
        return `
            <tr>
                <td>${user.id}</td>
                <td>${user.username}</td>
                <td>${user.email}</td>
                <td>${roleBadge}</td>
                <td>${user.reportCount || 0}</td>
                <td>${registered}</td>
                <td>${statusBadge}</td>
                <td>
                    <button class="btn btn-secondary btn-sm" onclick="editUser('${user.id}')">Edit</button>
                    ${user.role !== 'owner' ? `<button class="btn btn-danger btn-sm" onclick="deleteUser('${user.id}')">Delete</button>` : ''}
                </td>
            </tr>
        `;
    }).join('');
}

function getRoleBadge(role) {
    const badges = {
        'owner': '<span class="role-badge owner">Owner</span>',
        'admin': '<span class="role-badge admin">Admin</span>',
        'premium': '<span class="role-badge premium">Premium</span>',
        'user': '<span class="role-badge user">User</span>'
    };
    return badges[role] || badges['user'];
}

// Load pending accounts
async function loadPendingAccounts() {
    try {
        const response = await apiCall('/v2/admin/pending-accounts', {
            method: 'GET'
        });
        
        if (response.ok) {
            const data = await response.json();
            displayPendingAccounts(data.pending_accounts || []);
        }
    } catch (error) {
        console.error('Error loading pending accounts:', error);
        displayPendingAccounts([]);
    }
}

function displayPendingAccounts(accounts) {
    const tbody = document.getElementById('pendingAccountsBody');
    
    if (accounts.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" style="text-align: center;">No pending accounts</td></tr>';
        return;
    }
    
    tbody.innerHTML = accounts.map(account => {
        const registered = new Date(account.createdAt).toLocaleDateString() + ' ' + 
                          new Date(account.createdAt).toLocaleTimeString();
        
        return `
            <tr>
                <td>${account.username}</td>
                <td>${account.email}</td>
                <td>${registered}</td>
                <td>
                    <button class="btn btn-success btn-sm" onclick="approveAccount('${account.id}')">Approve</button>
                    <button class="btn btn-danger btn-sm" onclick="rejectAccount('${account.id}')">Reject</button>
                </td>
            </tr>
        `;
    }).join('');
}

async function approveAccount(userId) {
    if (!confirm('Are you sure you want to approve this account?')) {
        return;
    }
    
    try {
        const response = await apiCall(`/v2/admin/approve-account/${userId}`, {
            method: 'POST'
        });
        
        if (response.ok) {
            showNotification('Account approved successfully', 'success');
            loadPendingAccounts(); // Reload the list
        } else {
            const error = await response.json();
            showNotification(error.detail || 'Failed to approve account', 'error');
        }
    } catch (error) {
        console.error('Error approving account:', error);
        showNotification('Error approving account', 'error');
    }
}

async function rejectAccount(userId) {
    if (!confirm('Are you sure you want to reject and delete this account? This action cannot be undone.')) {
        return;
    }
    
    try {
        const response = await apiCall(`/v2/admin/reject-account/${userId}`, {
            method: 'POST'
        });
        
        if (response.ok) {
            showNotification('Account rejected and deleted', 'success');
            loadPendingAccounts(); // Reload the list
        } else {
            const error = await response.json();
            showNotification(error.detail || 'Failed to reject account', 'error');
        }
    } catch (error) {
        console.error('Error rejecting account:', error);
        showNotification('Error rejecting account', 'error');
    }
}

async function assignRole(userId, newRole) {
    try {
        const response = await apiCall(`/v2/admin/assign-role/${userId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ role: newRole })
        });
        
        if (response.ok) {
            showNotification('Role assigned successfully', 'success');
            closeEditUserModal();
            loadUsers(); // Reload users list
        } else {
            const error = await response.json();
            showNotification(error.detail || 'Failed to assign role', 'error');
        }
    } catch (error) {
        console.error('Error assigning role:', error);
        showNotification('Error assigning role', 'error');
    }
}

async function loadAllReports() {
    try {
        const response = await apiCall(`/v2/admin/reports?page=${currentReportsPage}&limit=50`, {
            method: 'GET'
        });
        
        if (response.ok) {
            const data = await response.json();
            displayReports(data.reports || []);
            updateReportsPagination(data.pagination || {});
        }
    } catch (error) {
        console.error('Error loading reports:', error);
        displayReports([]);
    }
}

function updateReportsPagination(pagination) {
    currentReportsPage = pagination.currentPage || 1;
    totalReportsPages = pagination.totalPages || 1;
    
    const pageInfo = document.getElementById('reportsPageInfo');
    const prevBtn = document.getElementById('prevReportsPage');
    const nextBtn = document.getElementById('nextReportsPage');
    
    if (pageInfo) pageInfo.textContent = `Page ${currentReportsPage} of ${totalReportsPages}`;
    if (prevBtn) prevBtn.disabled = currentReportsPage === 1;
    if (nextBtn) nextBtn.disabled = currentReportsPage === totalReportsPages;
}

function displayReports(reports) {
    const tbody = document.getElementById('reportsTableBody');
    
    if (reports.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" style="text-align: center; padding: 30px;">No reports found</td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = reports.map(report => {
        const statusBadge = report.status === 'success'
            ? '<span class="status-badge success">Success</span>'
            : '<span class="status-badge failed">Failed</span>';
        const timestamp = new Date(report.timestamp).toLocaleString();
        
        return `
            <tr>
                <td>${report.id}</td>
                <td>${report.username}</td>
                <td>${report.target}</td>
                <td>${report.method}</td>
                <td>${statusBadge}</td>
                <td>${timestamp}</td>
                <td>${report.ipAddress || 'N/A'}</td>
            </tr>
        `;
    }).join('');
}

async function loadSystemConfig() {
    try {
        const response = await apiCall('/v2/admin/config', {
            method: 'GET'
        });
        
        if (response.ok) {
            const data = await response.json();
            document.getElementById('maxReportsPerUser').value = data.maxReportsPerUser || 1000;
            document.getElementById('maxBulkTargets').value = data.maxBulkTargets || 200;
            document.getElementById('maxPremiumBulkTargets').value = data.maxPremiumBulkTargets || 500;
            document.getElementById('apiTimeout').value = data.apiTimeout || 30;
            document.getElementById('rateLimitPerMinute').value = data.rateLimitPerMinute || 60;
            document.getElementById('maintenanceMode').checked = data.maintenanceMode || false;
            document.getElementById('registrationEnabled').checked = data.registrationEnabled !== false;
            document.getElementById('requireApproval').checked = data.requireApproval || false;
        }
    } catch (error) {
        console.error('Error loading system config:', error);
    }
}

async function saveSystemConfig(e) {
    e.preventDefault();
    
    const config = {
        maxReportsPerUser: parseInt(document.getElementById('maxReportsPerUser').value),
        maxBulkTargets: parseInt(document.getElementById('maxBulkTargets').value),
        maxPremiumBulkTargets: parseInt(document.getElementById('maxPremiumBulkTargets').value),
        apiTimeout: parseInt(document.getElementById('apiTimeout').value),
        rateLimitPerMinute: parseInt(document.getElementById('rateLimitPerMinute').value),
        maintenanceMode: document.getElementById('maintenanceMode').checked,
        registrationEnabled: document.getElementById('registrationEnabled').checked,
        requireApproval: document.getElementById('requireApproval').checked
    };
    
    try {
        const response = await apiCall('/v2/admin/config', {
            method: 'PUT',
            body: JSON.stringify(config)
        });
        
        if (response.ok) {
            showNotification('Configuration saved successfully', 'success');
        } else {
            showNotification('Failed to save configuration', 'error');
        }
    } catch (error) {
        console.error('Error saving config:', error);
        showNotification('Error saving configuration', 'error');
    }
}

async function loadSystemLogs() {
    try {
        const response = await apiCall('/v2/admin/logs?limit=100', {
            method: 'GET'
        });
        
        if (response.ok) {
            const data = await response.json();
            displayLogs(data.logs || []);
        }
    } catch (error) {
        console.error('Error loading logs:', error);
        displayLogs([]);
    }
}

function displayLogs(logs) {
    const container = document.getElementById('logsContainer');
    
    if (logs.length === 0) {
        container.innerHTML = '<p style="text-align: center; color: var(--text-gray);">No logs available</p>';
        return;
    }
    
    container.innerHTML = logs.map(log => {
        const time = new Date(log.timestamp).toLocaleString();
        return `
            <div class="log-item">
                <span class="log-time">${time}</span>
                <span class="log-level ${log.level}">${log.level.toUpperCase()}</span>
                <span class="log-message">${log.message}</span>
            </div>
        `;
    }).join('');
}

async function clearSystemLogs() {
    if (!confirm('Are you sure you want to clear all system logs?')) return;
    
    try {
        const response = await apiCall('/v2/admin/logs', {
            method: 'DELETE'
        });
        
        if (response.ok) {
            showNotification('Logs cleared successfully', 'success');
            displayLogs([]);
        } else {
            showNotification('Failed to clear logs', 'error');
        }
    } catch (error) {
        console.error('Error clearing logs:', error);
        showNotification('Error clearing logs', 'error');
    }
}

function showAddUserModal() {
    document.getElementById('modalTitle').textContent = 'Add New User';
    document.getElementById('userEditForm').reset();
    document.getElementById('editUserId').value = '';
    document.getElementById('editPassword').required = true;
    document.getElementById('editPassword').placeholder = 'Enter password';
    document.getElementById('userModal').classList.add('active');
}

async function editUser(userId) {
    try {
        const response = await apiCall(`/v2/admin/users/${userId}`, {
            method: 'GET'
        });
        
        if (response.ok) {
            const user = await response.json();
            document.getElementById('modalTitle').textContent = 'Edit User';
            document.getElementById('editUserId').value = user.id;
            document.getElementById('editUsername').value = user.username;
            document.getElementById('editEmail').value = user.email;
            document.getElementById('editPassword').value = '';
            document.getElementById('editPassword').required = false;
            document.getElementById('editPassword').placeholder = 'Leave blank to keep current password';
            document.getElementById('editRole').value = user.role;
            document.getElementById('editActive').checked = user.isActive;
            document.getElementById('userModal').classList.add('active');
        }
    } catch (error) {
        console.error('Error loading user:', error);
        showNotification('Error loading user data', 'error');
    }
}

async function saveUserChanges(e) {
    e.preventDefault();
    
    const userId = document.getElementById('editUserId').value;
    const password = document.getElementById('editPassword').value;
    
    const userData = {
        username: document.getElementById('editUsername').value,
        email: document.getElementById('editEmail').value,
        role: document.getElementById('editRole').value,
        isActive: document.getElementById('editActive').checked
    };
    
    // Add password if provided (required for new users, optional for edits)
    if (password || !userId) {
        userData.password = password;
    }
    
    const url = userId 
        ? `/v2/admin/users/${userId}`
        : '/v2/admin/users';
    
    const method = userId ? 'PUT' : 'POST';
    
    try {
        const response = await apiCall(url, {
            method: method,
            body: JSON.stringify(userData)
        });
        
        if (response.ok) {
            showNotification('User saved successfully', 'success');
            closeModal();
            loadUsers();
        } else {
            const data = await response.json();
            showNotification(data.detail || data.message || 'Failed to save user', 'error');
        }
    } catch (error) {
        console.error('Error saving user:', error);
        showNotification('Error saving user', 'error');
    }
}

async function deleteUser(userId) {
    if (!confirm('Are you sure you want to delete this user?')) return;
    
    try {
        const response = await apiCall(`/v2/admin/users/${userId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            showNotification('User deleted successfully', 'success');
            loadUsers();
        } else {
            showNotification('Failed to delete user', 'error');
        }
    } catch (error) {
        console.error('Error deleting user:', error);
        showNotification('Error deleting user', 'error');
    }
}

function filterUsers() {
    const searchTerm = document.getElementById('userSearch').value.toLowerCase();
    const rows = document.querySelectorAll('#usersTableBody tr');
    
    rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        row.style.display = text.includes(searchTerm) ? '' : 'none';
    });
}

async function exportReports() {
    try {
        const response = await apiCall('/v2/admin/reports/export', {
            method: 'GET'
        });
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `swatnfo_reports_${Date.now()}.csv`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            showNotification('Reports exported successfully', 'success');
        } else {
            showNotification('Failed to export reports', 'error');
        }
    } catch (error) {
        console.error('Error exporting reports:', error);
        showNotification('Error exporting reports', 'error');
    }
}

function closeModal() {
    const userModal = document.getElementById('userModal');
    const blacklistModal = document.getElementById('blacklistModal');
    if (userModal) userModal.classList.remove('active');
    if (blacklistModal) blacklistModal.classList.remove('active');
}

function showNotification(message, type) {
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 25px;
        border-radius: 8px;
        font-weight: 600;
        z-index: 2000;
        animation: slideIn 0.3s ease;
    `;
    
    if (type === 'success') {
        notification.style.backgroundColor = 'rgba(46, 204, 113, 0.9)';
        notification.style.color = '#fff';
    } else {
        notification.style.backgroundColor = 'rgba(231, 76, 60, 0.9)';
        notification.style.color = '#fff';
    }
    
    notification.textContent = message;
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.opacity = '0';
        notification.style.transition = 'opacity 0.3s ease';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

function logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    sessionStorage.removeItem('token');
    window.location.href = '/login';
}

// Make functions globally accessible for onclick handlers
window.editUser = editUser;
window.deleteUser = deleteUser;
window.removeFromBlacklist = removeFromBlacklist;
window.viewReportDetails = function(id) {
    console.log('Viewing report:', id);
};


// ==================== BLACKLIST FUNCTIONS ====================

async function loadBlacklist() {
    try {
        const response = await apiCall('/v2/admin/blacklist', {
            method: 'GET'
        });
        
        if (response.ok) {
            const data = await response.json();
            displayBlacklist(data.blacklist || []);
            updateBlacklistStats(data.stats || { total: 0, blocked: 0 });
        }
    } catch (error) {
        console.error('Error loading blacklist:', error);
        document.getElementById('blacklistTableBody').innerHTML = `
            <tr><td colspan="6" style="text-align: center; color: var(--danger);">Error loading blacklist</td></tr>
        `;
    }
}

function displayBlacklist(blacklist) {
    const tbody = document.getElementById('blacklistTableBody');
    
    if (blacklist.length === 0) {
        tbody.innerHTML = `
            <tr><td colspan="6" style="text-align: center; color: var(--text-gray);">No blacklisted accounts</td></tr>
        `;
        return;
    }
    
    tbody.innerHTML = blacklist.map(entry => `
        <tr>
            <td><strong>@${entry.username}</strong></td>
            <td><span class="badge">${entry.reason}</span></td>
            <td>${entry.added_by || 'System'}</td>
            <td>${new Date(entry.created_at).toLocaleDateString()}</td>
            <td><span class="badge badge-danger">${entry.blocked_attempts || 0}</span></td>
            <td>
                <button onclick="removeFromBlacklist('${entry.username}')" class="btn btn-danger btn-sm">Remove</button>
            </td>
        </tr>
    `).join('');
}

function updateBlacklistStats(stats) {
    document.getElementById('totalBlacklisted').textContent = stats.total || 0;
    document.getElementById('blockedReports').textContent = stats.blocked || 0;
}

function showBlacklistModal() {
    console.log('showBlacklistModal called');
    const modal = document.getElementById('blacklistModal');
    console.log('Modal element:', modal);
    if (modal) {
        modal.classList.add('active');
        const form = document.getElementById('blacklistAddForm');
        if (form) form.reset();
    } else {
        console.error('Blacklist modal not found!');
    }
}

// Make showBlacklistModal globally accessible
window.showBlacklistModal = showBlacklistModal;

async function addToBlacklist(e) {
    e.preventDefault();
    
    const username = document.getElementById('blacklistUsername').value.trim().replace('@', '');
    const reason = document.getElementById('blacklistReason').value;
    const notes = document.getElementById('blacklistNotes').value.trim();
    
    if (!username || !reason) {
        showNotification('Please fill in all required fields', 'error');
        return;
    }
    
    try {
        const response = await apiCall('/v2/admin/blacklist', {
            method: 'POST',
            body: JSON.stringify({
                username: username,
                reason: reason,
                notes: notes
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showNotification('Account added to blacklist successfully', 'success');
            closeModal();
            loadBlacklist();
        } else {
            showNotification(data.message || 'Failed to add to blacklist', 'error');
        }
    } catch (error) {
        console.error('Error adding to blacklist:', error);
        showNotification('Connection error', 'error');
    }
}

async function removeFromBlacklist(username) {
    if (!confirm(`Remove @${username} from blacklist?`)) {
        return;
    }
    
    try {
        const response = await apiCall(`/v2/admin/blacklist/${username}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showNotification('Account removed from blacklist', 'success');
            loadBlacklist();
        } else {
            showNotification(data.message || 'Failed to remove from blacklist', 'error');
        }
    } catch (error) {
        console.error('Error removing from blacklist:', error);
        showNotification('Connection error', 'error');
    }
}

function filterBlacklist() {
    const searchTerm = document.getElementById('blacklistSearch').value.toLowerCase();
    const rows = document.querySelectorAll('#blacklistTableBody tr');
    
    rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        row.style.display = text.includes(searchTerm) ? '' : 'none';
    });
}

