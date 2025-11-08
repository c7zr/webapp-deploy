// Settings Page Handler
document.addEventListener('DOMContentLoaded', async () => {
    await requireAuth();
    initProfileDropdown();
    loadAccountData();
    loadCredentials();
    initializeForms();
});

function checkAuth() {
    const token = localStorage.getItem('token') || sessionStorage.getItem('token');
    if (!token) {
        window.location.href = '/login';
        return;
    }
}

function loadAccountData() {
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    if (user.username) {
        document.getElementById('accountUsername').value = user.username;
        document.getElementById('accountEmail').value = user.email || '';
    }
}

async function loadCredentials() {
    const token = localStorage.getItem('token') || sessionStorage.getItem('token');
    
    try {
        const response = await fetch(`${window.location.origin}/v2/credentials`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            if (data.credentials) {
                document.getElementById('sessionId').value = data.credentials.sessionId || '';
                document.getElementById('csrfToken').value = data.credentials.csrfToken || '';
                
                if (data.credentials.isValid) {
                    updateCredentialsStatus(true);
                } else {
                    updateCredentialsStatus(false);
                }
            }
        }
    } catch (error) {
        console.error('Error loading credentials:', error);
    }
}

function initializeForms() {
    // Account form
    document.getElementById('accountForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        await updateAccount();
    });
    
    // Credentials form
    document.getElementById('credentialsForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        await saveCredentials();
    });
    
    document.getElementById('testCredentials').addEventListener('click', async () => {
        await testCredentials();
    });
    
    // Password form
    document.getElementById('passwordForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        await changePassword();
    });
    
    // Danger zone
    document.getElementById('clearHistory').addEventListener('click', async () => {
        if (confirm('Are you sure you want to clear all your report history? This cannot be undone.')) {
            await clearHistory();
        }
    });
    
    document.getElementById('deleteAccount').addEventListener('click', async () => {
        if (confirm('Are you sure you want to DELETE your account? This is PERMANENT and cannot be undone!')) {
            const confirmText = prompt('Type "DELETE" to confirm:');
            if (confirmText === 'DELETE') {
                await deleteAccount();
            }
        }
    });
}

async function updateAccount() {
    const token = localStorage.getItem('token') || sessionStorage.getItem('token');
    const email = document.getElementById('accountEmail').value.trim();
    
    try {
        const response = await fetch(`${window.location.origin}/v2/user/update`, {
            method: 'PUT',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ email })
        });
        
        if (response.ok) {
            showMessage('Account updated successfully', 'success');
            const data = await response.json();
            localStorage.setItem('user', JSON.stringify(data.user));
        } else {
            showMessage('Failed to update account', 'error');
        }
    } catch (error) {
        console.error('Error updating account:', error);
        showMessage('Error updating account', 'error');
    }
}

async function saveCredentials() {
    const token = localStorage.getItem('token') || sessionStorage.getItem('token');
    const sessionId = document.getElementById('sessionId').value.trim();
    const csrfToken = document.getElementById('csrfToken').value.trim();
    
    if (!sessionId || !csrfToken) {
        showMessage('Please enter both sessionid and csrf_token', 'error');
        return;
    }
    
    try {
        const response = await fetch(`${window.location.origin}/v2/credentials`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                sessionId: sessionId,
                csrfToken: csrfToken
            })
        });
        
        if (response.ok) {
            showMessage('Credentials saved successfully', 'success');
            updateCredentialsStatus(true);
        } else {
            showMessage('Failed to save credentials', 'error');
        }
    } catch (error) {
        console.error('Error saving credentials:', error);
        showMessage('Error saving credentials', 'error');
    }
}

async function testCredentials() {
    const token = localStorage.getItem('token') || sessionStorage.getItem('token');
    
    showMessage('Testing credentials...', 'info');
    
    try {
        const response = await fetch(`${window.location.origin}/v2/credentials/test`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (response.ok && data.valid) {
            showMessage('✅ Credentials are valid and working!', 'success');
            updateCredentialsStatus(true);
        } else {
            showMessage('❌ Credentials are invalid or expired', 'error');
            updateCredentialsStatus(false);
        }
    } catch (error) {
        console.error('Error testing credentials:', error);
        showMessage('Error testing credentials', 'error');
    }
}

async function changePassword() {
    const token = localStorage.getItem('token') || sessionStorage.getItem('token');
    const currentPassword = document.getElementById('currentPassword').value;
    const newPassword = document.getElementById('newPassword').value;
    const confirmPassword = document.getElementById('confirmNewPassword').value;
    
    if (newPassword !== confirmPassword) {
        showMessage('New passwords do not match', 'error');
        return;
    }
    
    if (newPassword.length < 8) {
        showMessage('Password must be at least 8 characters', 'error');
        return;
    }
    
    try {
        const response = await fetch(`${window.location.origin}/v2/user/password`, {
            method: 'PUT',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                currentPassword: currentPassword,
                newPassword: newPassword
            })
        });
        
        if (response.ok) {
            showMessage('Password changed successfully', 'success');
            document.getElementById('passwordForm').reset();
        } else {
            const data = await response.json();
            showMessage(data.message || 'Failed to change password', 'error');
        }
    } catch (error) {
        console.error('Error changing password:', error);
        showMessage('Error changing password', 'error');
    }
}

async function clearHistory() {
    const token = localStorage.getItem('token') || sessionStorage.getItem('token');
    
    try {
        const response = await fetch(`${window.location.origin}/v2/reports/clear`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        
        if (response.ok) {
            showMessage('History cleared successfully', 'success');
        } else {
            showMessage('Failed to clear history', 'error');
        }
    } catch (error) {
        console.error('Error clearing history:', error);
        showMessage('Error clearing history', 'error');
    }
}

async function deleteAccount() {
    const token = localStorage.getItem('token') || sessionStorage.getItem('token');
    
    try {
        const response = await fetch(`${window.location.origin}/v2/user/delete`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        
        if (response.ok) {
            alert('Account deleted successfully');
            logout();
        } else {
            showMessage('Failed to delete account', 'error');
        }
    } catch (error) {
        console.error('Error deleting account:', error);
        showMessage('Error deleting account', 'error');
    }
}

function updateCredentialsStatus(isValid) {
    const statusDiv = document.getElementById('credentialsStatus');
    const dot = statusDiv.querySelector('.status-dot');
    const text = statusDiv.querySelector('.status-text');
    
    if (isValid) {
        dot.classList.add('active');
        text.textContent = 'Credentials configured and valid';
        text.style.color = 'var(--success)';
    } else {
        dot.classList.remove('active');
        text.textContent = 'Not configured or invalid';
        text.style.color = 'var(--text-gray)';
    }
}

function showMessage(message, type) {
    // Create a temporary message element
    const messageDiv = document.createElement('div');
    messageDiv.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 25px;
        border-radius: 8px;
        font-weight: 600;
        z-index: 1000;
        animation: slideIn 0.3s ease;
    `;
    
    if (type === 'success') {
        messageDiv.style.backgroundColor = 'rgba(46, 204, 113, 0.9)';
        messageDiv.style.color = '#fff';
    } else if (type === 'error') {
        messageDiv.style.backgroundColor = 'rgba(231, 76, 60, 0.9)';
        messageDiv.style.color = '#fff';
    } else {
        messageDiv.style.backgroundColor = 'rgba(155, 89, 182, 0.9)';
        messageDiv.style.color = '#fff';
    }
    
    messageDiv.textContent = message;
    document.body.appendChild(messageDiv);
    
    setTimeout(() => {
        messageDiv.style.opacity = '0';
        messageDiv.style.transition = 'opacity 0.3s ease';
        setTimeout(() => messageDiv.remove(), 300);
    }, 3000);
}

function logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    sessionStorage.removeItem('token');
    window.location.href = '/login';
}

