// Reporting Page Handler
document.addEventListener('DOMContentLoaded', async () => {
    await requireAuth();
    initProfileDropdown();
    initializeReporting();
    loadCredentials();
});

let reportingActive = false;
let reportingAborted = false;

function initializeReporting() {
    // Mode switching
    document.getElementById('singleModeBtn').addEventListener('click', () => {
        switchMode('single');
    });
    
    document.getElementById('bulkModeBtn').addEventListener('click', () => {
        switchMode('bulk');
    });
    
    // Input method switching
    document.getElementById('manualInputBtn').addEventListener('click', () => {
        switchInputMethod('manual');
    });
    
    document.getElementById('fileUploadBtn').addEventListener('click', () => {
        switchInputMethod('file');
    });
    
    // Credentials buttons
    document.getElementById('saveCredsBtn').addEventListener('click', saveCredentials);
    document.getElementById('clearCredsBtn').addEventListener('click', clearCredentials);
    
    // Start reporting buttons
    document.getElementById('startSingleReport').addEventListener('click', startSingleReport);
    document.getElementById('startBulkReport').addEventListener('click', startBulkReport);
    
    // Control buttons
    document.getElementById('stopReport').addEventListener('click', stopReporting);
    document.getElementById('newReport').addEventListener('click', resetReporting);
    document.getElementById('viewHistory').addEventListener('click', () => {
        window.location.href = '/history';
    });
    
    // File upload handler
    document.getElementById('targetsFile').addEventListener('change', handleFileUpload);
}

async function loadCredentials() {
    try {
        const response = await apiCall('/v2/credentials', { method: 'GET' });
        if (response.ok) {
            const data = await response.json();
            if (data.configured) {
                document.getElementById('instagramSessionId').value = '••••••••••••';
                document.getElementById('instagramCsrfToken').value = '••••••••••••';
                document.getElementById('saveCredentials').checked = true;
                updateCredentialsStatus(true, 'Credentials saved');
            }
        }
    } catch (error) {
        console.error('Error loading credentials:', error);
    }
}

async function saveCredentials() {
    const sessionId = document.getElementById('instagramSessionId').value.trim();
    const csrfToken = document.getElementById('instagramCsrfToken').value.trim();
    
    if (!sessionId || !csrfToken || sessionId === '••••••••••••') {
        alert('Please enter both Session ID and CSRF Token');
        return;
    }
    
    try {
        const response = await apiCall('/v2/credentials', {
            method: 'POST',
            body: JSON.stringify({
                sessionId: sessionId,
                csrfToken: csrfToken
            })
        });
        
        if (response.ok) {
            updateCredentialsStatus(true, 'Credentials saved successfully');
            document.getElementById('instagramSessionId').value = '••••••••••••';
            document.getElementById('instagramCsrfToken').value = '••••••••••••';
            alert('Credentials saved successfully!');
        } else {
            const data = await response.json();
            alert('Error: ' + (data.detail || 'Failed to save credentials'));
        }
    } catch (error) {
        alert('Error saving credentials: ' + error.message);
    }
}

async function clearCredentials() {
    if (!confirm('Are you sure you want to clear saved credentials?')) {
        return;
    }
    
    try {
        const response = await apiCall('/v2/credentials', { method: 'DELETE' });
        if (response.ok) {
            document.getElementById('instagramSessionId').value = '';
            document.getElementById('instagramCsrfToken').value = '';
            document.getElementById('saveCredentials').checked = false;
            updateCredentialsStatus(false, 'No credentials saved');
            alert('Credentials cleared successfully');
        }
    } catch (error) {
        alert('Error clearing credentials: ' + error.message);
    }
}

function updateCredentialsStatus(isValid, message) {
    const statusEl = document.getElementById('credentialsStatus');
    const indicator = statusEl.querySelector('.status-indicator');
    const text = statusEl.querySelector('.status-text');
    
    if (isValid) {
        indicator.style.background = '#4CAF50';
        statusEl.style.borderColor = '#4CAF50';
    } else {
        indicator.style.background = '#f44336';
        statusEl.style.borderColor = '#f44336';
    }
    
    text.textContent = message;
}

function switchMode(mode) {
    if (mode === 'single') {
        document.getElementById('singleModeBtn').classList.add('active');
        document.getElementById('bulkModeBtn').classList.remove('active');
        document.getElementById('singleReportSection').style.display = 'block';
        document.getElementById('bulkReportSection').style.display = 'none';
    } else {
        document.getElementById('singleModeBtn').classList.remove('active');
        document.getElementById('bulkModeBtn').classList.add('active');
        document.getElementById('singleReportSection').style.display = 'none';
        document.getElementById('bulkReportSection').style.display = 'block';
    }
}

function switchInputMethod(method) {
    if (method === 'manual') {
        document.getElementById('manualInputBtn').classList.add('active');
        document.getElementById('fileUploadBtn').classList.remove('active');
        document.getElementById('manualInputSection').style.display = 'block';
        document.getElementById('fileUploadSection').style.display = 'none';
    } else {
        document.getElementById('manualInputBtn').classList.remove('active');
        document.getElementById('fileUploadBtn').classList.add('active');
        document.getElementById('manualInputSection').style.display = 'none';
        document.getElementById('fileUploadSection').style.display = 'block';
    }
}

function handleFileUpload(e) {
    const file = e.target.files[0];
    if (!file) return;
    
    const reader = new FileReader();
    reader.onload = (event) => {
        document.getElementById('bulkTargets').value = event.target.result;
    };
    reader.readAsText(file);
}

async function startSingleReport() {
    const target = document.getElementById('singleTarget').value.trim();
    const method = document.getElementById('reportMethod').value;
    const count = parseInt(document.getElementById('reportCount').value);
    
    if (!target) {
        showError('Please enter a target username');
        return;
    }
    
    if (count < 1 || count > 1000) {
        showError('Report count must be between 1 and 1000');
        return;
    }
    
    showProgressSection();
    reportingActive = true;
    reportingAborted = false;
    
    let success = 0;
    let failed = 0;
    
    for (let i = 0; i < count; i++) {
        if (reportingAborted) break;
        
        updateProgress(target, i + 1, count, success, failed);
        
        const result = await sendReport(target, method);
        
        if (result.success) {
            success++;
            addLogEntry(`✅ Report ${i + 1}/${count} successful`, 'success');
        } else {
            failed++;
            addLogEntry(`❌ Report ${i + 1}/${count} failed: ${result.error}`, 'error');
        }
        
        updateProgress(target, i + 1, count, success, failed);
        
        // Small delay between reports
        await sleep(500);
    }
    
    reportingActive = false;
    showResults(count, success, failed);
}

async function startBulkReport() {
    const method = document.getElementById('bulkMethod').value;
    const targetsText = document.getElementById('bulkTargets').value.trim();
    
    if (!targetsText) {
        alert('Please enter at least one username');
        return;
    }
    
    // Check user role first
    try {
        const profileResponse = await apiCall('/v2/user/profile', { method: 'GET' });
        if (profileResponse.ok) {
            const profileData = await profileResponse.json();
            const userRole = profileData.role;
            
            // Only allow premium, admin, and owner roles
            if (!['premium', 'admin', 'owner'].includes(userRole)) {
                alert('❌ Bulk Reporting is a Premium Feature!\n\n' +
                      'Bulk reporting is exclusive to Premium users.\n\n' +
                      'Upgrade to Premium to:\n' +
                      '• Report up to 500 accounts at once\n' +
                      '• Unlimited daily reports\n' +
                      '• Priority support\n\n' +
                      'Contact SWATNFO or Xefi for payment to upgrade your account.');
                return;
            }
        }
    } catch (error) {
        console.error('Error checking user role:', error);
        alert('Error verifying account status. Please try again.');
        return;
    }
    
    const targets = targetsText.split('\n').filter(t => t.trim()).map(t => t.trim());
    
    if (targets.length === 0) {
        showError('No valid targets found');
        return;
    }
    
    if (targets.length > 200) {
        showError('Maximum 200 targets allowed');
        return;
    }
    
    showProgressSection();
    reportingActive = true;
    reportingAborted = false;
    
    let totalSuccess = 0;
    let totalFailed = 0;
    let totalReports = targets.length;
    
    for (let i = 0; i < targets.length; i++) {
        if (reportingAborted) break;
        
        const target = targets[i];
        updateProgress(target, i + 1, totalReports, totalSuccess, totalFailed);
        
        const result = await sendReport(target, method);
        
        if (result.success) {
            totalSuccess++;
            addLogEntry(`✅ ${target} - Report successful`, 'success');
        } else {
            totalFailed++;
            addLogEntry(`❌ ${target} - Report failed: ${result.error}`, 'error');
        }
        
        updateProgress(target, i + 1, totalReports, totalSuccess, totalFailed);
        
        // Small delay between targets
        await sleep(800);
    }
    
    reportingActive = false;
    showResults(totalReports, totalSuccess, totalFailed);
}

async function sendReport(target, method) {
    try {
        const response = await apiCall('/v2/reports/send', {
            method: 'POST',
            body: JSON.stringify({
                target: target,
                method: method
            })
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            return { success: true };
        } else {
            return { success: false, error: data.message || 'Unknown error' };
        }
    } catch (error) {
        console.error('Report error:', error);
        return { success: false, error: 'Network error' };
    }
}

function updateProgress(target, current, total, success, failed) {
    document.getElementById('currentTarget').textContent = target;
    document.getElementById('progressText').textContent = `${current}/${total}`;
    document.getElementById('successCount').textContent = success;
    document.getElementById('failCount').textContent = failed;
    
    const percentage = (current / total) * 100;
    document.getElementById('progressBar').style.width = percentage + '%';
}

function addLogEntry(message, type) {
    const logContainer = document.getElementById('liveLog');
    const entry = document.createElement('div');
    entry.className = `log-entry ${type}`;
    entry.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
    logContainer.appendChild(entry);
    logContainer.scrollTop = logContainer.scrollHeight;
}

function showProgressSection() {
    document.getElementById('singleReportSection').style.display = 'none';
    document.getElementById('bulkReportSection').style.display = 'none';
    document.getElementById('resultsSection').style.display = 'none';
    document.getElementById('progressSection').style.display = 'block';
    
    // Clear log
    document.getElementById('liveLog').innerHTML = '';
}

function showResults(total, success, failed) {
    document.getElementById('progressSection').style.display = 'none';
    document.getElementById('resultsSection').style.display = 'block';
    
    document.getElementById('totalReported').textContent = total;
    document.getElementById('totalSuccess').textContent = success;
    document.getElementById('totalFailed').textContent = failed;
}

function stopReporting() {
    reportingAborted = true;
    addLogEntry('⚠️ Reporting stopped by user', 'error');
}

function resetReporting() {
    document.getElementById('resultsSection').style.display = 'none';
    document.getElementById('singleReportSection').style.display = 'block';
    
    // Reset inputs
    document.getElementById('singleTarget').value = '';
    document.getElementById('reportCount').value = '1';
    document.getElementById('bulkTargets').value = '';
    
    // Reset to single mode
    switchMode('single');
}

function showError(message) {
    alert(message); // Simple alert for now
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

