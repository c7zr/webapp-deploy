// Settings Page Handler
document.addEventListener('DOMContentLoaded', async () => {
    await requireAuth();
    initProfileDropdown();
    loadAccountData();
    
    // Load credentials with retry logic
    let retryCount = 0;
    const maxRetries = 3;
    
    const tryLoadCredentials = async () => {
        try {
            await loadCredentials();
            console.log('✅ Credentials loaded successfully');
        } catch (error) {
            retryCount++;
            if (retryCount < maxRetries) {
                console.log(`⚠️ Retrying credential load (${retryCount}/${maxRetries})...`);
                setTimeout(tryLoadCredentials, 1000);
            } else {
                console.error('❌ Failed to load credentials after', maxRetries, 'attempts');
            }
        }
    };
    
    await tryLoadCredentials();
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
    console.log('🔄 Loading credentials...');
    
    try {
        const response = await fetch(`${window.location.origin}/v2/credentials`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        
        console.log('Credentials API response status:', response.status);
        
        if (response.ok) {
            const data = await response.json();
            console.log('Credentials data:', data);
            
            if (data.credentials && data.credentials.sessionId && data.credentials.csrfToken) {
                // Populate input fields
                const sessionIdInput = document.getElementById('sessionId');
                const csrfTokenInput = document.getElementById('csrfToken');
                
                if (sessionIdInput) {
                    sessionIdInput.value = data.credentials.sessionId;
                    console.log('✅ SessionId loaded:', data.credentials.sessionId.substring(0, 20) + '...');
                }
                if (csrfTokenInput) {
                    csrfTokenInput.value = data.credentials.csrfToken;
                    console.log('✅ CsrfToken loaded:', data.credentials.csrfToken.substring(0, 20) + '...');
                }
                
                // Also store in localStorage as backup
                localStorage.setItem('instagram_sessionId', data.credentials.sessionId);
                localStorage.setItem('instagram_csrfToken', data.credentials.csrfToken);
                
                if (data.credentials.isValid) {
                    updateCredentialsStatus(true);
                } else {
                    updateCredentialsStatus(false);
                }
            } else {
                console.log('⚠️ No credentials found in database, checking localStorage...');
                // Try loading from localStorage as fallback
                const savedSessionId = localStorage.getItem('instagram_sessionId');
                const savedCsrfToken = localStorage.getItem('instagram_csrfToken');
                
                if (savedSessionId && savedCsrfToken) {
                    const sessionIdInput = document.getElementById('sessionId');
                    const csrfTokenInput = document.getElementById('csrfToken');
                    
                    if (sessionIdInput) sessionIdInput.value = savedSessionId;
                    if (csrfTokenInput) csrfTokenInput.value = savedCsrfToken;
                    console.log('✅ Loaded credentials from localStorage');
                }
            }
        } else {
            console.error('❌ Failed to load credentials from API');
            // Try loading from localStorage as fallback
            const savedSessionId = localStorage.getItem('instagram_sessionId');
            const savedCsrfToken = localStorage.getItem('instagram_csrfToken');
            
            if (savedSessionId && savedCsrfToken) {
                const sessionIdInput = document.getElementById('sessionId');
                const csrfTokenInput = document.getElementById('csrfToken');
                
                if (sessionIdInput) sessionIdInput.value = savedSessionId;
                if (csrfTokenInput) csrfTokenInput.value = savedCsrfToken;
                console.log('✅ Loaded credentials from localStorage (fallback)');
            }
        }
    } catch (error) {
        console.error('Error loading credentials:', error);
        
        // Try loading from localStorage as fallback
        const savedSessionId = localStorage.getItem('instagram_sessionId');
        const savedCsrfToken = localStorage.getItem('instagram_csrfToken');
        
        if (savedSessionId && savedCsrfToken) {
            const sessionIdInput = document.getElementById('sessionId');
            const csrfTokenInput = document.getElementById('csrfToken');
            
            if (sessionIdInput) sessionIdInput.value = savedSessionId;
            if (csrfTokenInput) csrfTokenInput.value = savedCsrfToken;
            console.log('✅ Loaded credentials from localStorage (error fallback)');
        }
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
    
    console.log('💾 Saving credentials...');
    console.log('SessionId length:', sessionId.length);
    console.log('CsrfToken length:', csrfToken.length);
    
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
        
        const responseData = await response.json();
        console.log('Save response:', responseData);
        
        if (response.ok && responseData.success) {
            // Save to localStorage for persistence
            localStorage.setItem('instagram_sessionId', sessionId);
            localStorage.setItem('instagram_csrfToken', csrfToken);
            
            console.log('✅ Credentials saved successfully');
            showMessage('✅ Credentials saved successfully! They will persist across sessions.', 'success');
            updateCredentialsStatus(true);
            
            // Reload credentials to verify they were saved
            setTimeout(() => {
                loadCredentials();
            }, 500);
        } else {
            console.error('❌ Failed to save:', responseData);
            showMessage(`Failed to save credentials: ${responseData.message || 'Unknown error'}`, 'error');
        }
    } catch (error) {
        console.error('Error saving credentials:', error);
        showMessage('Error saving credentials. Check console for details.', 'error');
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

