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
    
    document.getElementById('massModeBtn').addEventListener('click', () => {
        switchMode('mass');
    });
    
    document.getElementById('scheduleModeBtn').addEventListener('click', () => {
        switchMode('schedule');
        loadScheduledReports();
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
    document.getElementById('startMassReport').addEventListener('click', startMassReport);
    
    // Schedule buttons
    document.getElementById('createSchedule').addEventListener('click', createScheduledReport);
    document.getElementById('refreshScheduled').addEventListener('click', loadScheduledReports);
    
    // Control buttons
    document.getElementById('stopReport').addEventListener('click', stopReporting);
    document.getElementById('newReport').addEventListener('click', resetReporting);
    document.getElementById('viewHistory').addEventListener('click', () => {
        window.location.href = '/history';
    });
    
    // File upload handler
    document.getElementById('targetsFile').addEventListener('change', handleFileUpload);
    
    // Set minimum datetime to now
    const now = new Date();
    now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
    document.getElementById('scheduleDateTime').min = now.toISOString().slice(0, 16);
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
                
                // Check if expired
                if (data.expired) {
                    updateCredentialsStatus(false, '⚠️ Credentials expired - Please update');
                    showExpiryAlert('Your Instagram credentials have expired! Please update them to continue reporting.');
                } else if (data.credentials && data.credentials.daysUntilExpiry !== null) {
                    if (data.credentials.daysUntilExpiry <= 7) {
                        updateCredentialsStatus(true, `⚠️ Expires in ${data.credentials.daysUntilExpiry} days`);
                        showExpiryWarning(`Your credentials will expire in ${data.credentials.daysUntilExpiry} days. Please update them soon.`);
                    } else {
                        updateCredentialsStatus(true, `✅ Valid (expires in ${data.credentials.daysUntilExpiry} days)`);
                    }
                } else {
                    updateCredentialsStatus(true, 'Credentials saved');
                }
            }
        }
    } catch (error) {
        console.error('Error loading credentials:', error);
    }
}

function showExpiryAlert(message) {
    const alertBox = document.createElement('div');
    alertBox.style.cssText = `
        position: fixed;
        top: 80px;
        right: 20px;
        background: linear-gradient(135deg, #f44336, #e53935);
        color: white;
        padding: 16px 20px;
        border-radius: 12px;
        box-shadow: 0 8px 32px rgba(244, 67, 54, 0.4);
        z-index: 9999;
        max-width: 400px;
        animation: slideInRight 0.3s ease;
        border: 2px solid rgba(255, 255, 255, 0.3);
    `;
    alertBox.innerHTML = `
        <div style="display: flex; align-items: start; gap: 12px;">
            <span style="font-size: 24px;">⚠️</span>
            <div style="flex: 1;">
                <strong style="display: block; margin-bottom: 4px;">Credentials Expired!</strong>
                <p style="margin: 0; font-size: 14px; opacity: 0.95;">${message}</p>
            </div>
            <button onclick="this.parentElement.parentElement.remove()" style="
                background: none;
                border: none;
                color: white;
                font-size: 24px;
                cursor: pointer;
                padding: 0;
                line-height: 1;
            ">×</button>
        </div>
    `;
    document.body.appendChild(alertBox);
    
    // Auto-remove after 3 seconds
    setTimeout(() => alertBox.remove(), 3000);
}

function showExpiryWarning(message) {
    const warningBox = document.createElement('div');
    warningBox.style.cssText = `
        position: fixed;
        top: 80px;
        right: 20px;
        background: linear-gradient(135deg, #ff9800, #fb8c00);
        color: white;
        padding: 16px 20px;
        border-radius: 12px;
        box-shadow: 0 8px 32px rgba(255, 152, 0, 0.4);
        z-index: 9999;
        max-width: 400px;
        animation: slideInRight 0.3s ease;
        border: 2px solid rgba(255, 255, 255, 0.3);
    `;
    warningBox.innerHTML = `
        <div style="display: flex; align-items: start; gap: 12px;">
            <span style="font-size: 24px;">⏰</span>
            <div style="flex: 1;">
                <strong style="display: block; margin-bottom: 4px;">Expiring Soon</strong>
                <p style="margin: 0; font-size: 14px; opacity: 0.95;">${message}</p>
            </div>
            <button onclick="this.parentElement.parentElement.remove()" style="
                background: none;
                border: none;
                color: white;
                font-size: 24px;
                cursor: pointer;
                padding: 0;
                line-height: 1;
            ">×</button>
        </div>
    `;
    document.body.appendChild(warningBox);
    
    // Auto-remove after 3 seconds
    setTimeout(() => warningBox.remove(), 3000);
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
    // Hide all sections
    document.getElementById('singleReportSection').style.display = 'none';
    document.getElementById('bulkReportSection').style.display = 'none';
    document.getElementById('massReportSection').style.display = 'none';
    document.getElementById('scheduleReportSection').style.display = 'none';
    
    // Remove all active states
    document.getElementById('singleModeBtn').classList.remove('active');
    document.getElementById('bulkModeBtn').classList.remove('active');
    document.getElementById('massModeBtn').classList.remove('active');
    document.getElementById('scheduleModeBtn').classList.remove('active');
    
    // Show selected mode
    if (mode === 'single') {
        document.getElementById('singleModeBtn').classList.add('active');
        document.getElementById('singleReportSection').style.display = 'block';
    } else if (mode === 'bulk') {
        document.getElementById('bulkModeBtn').classList.add('active');
        document.getElementById('bulkReportSection').style.display = 'block';
    } else if (mode === 'mass') {
        document.getElementById('massModeBtn').classList.add('active');
        document.getElementById('massReportSection').style.display = 'block';
    } else if (mode === 'schedule') {
        document.getElementById('scheduleModeBtn').classList.add('active');
        document.getElementById('scheduleReportSection').style.display = 'block';
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
    const count = parseInt(document.getElementById('reportCount').value) || 1;
    
    if (!target) {
        showError('Please enter a target username');
        return;
    }
    
    if (count < 1 || count > 20) {
        showError('Report count must be between 1 and 20');
        return;
    }
    
    showProgressSection();
    reportingActive = true;
    reportingAborted = false;
    
    addLogEntry(`🚀 Starting ${count} report(s) for @${target} with method: ${method}`, 'info');
    
    // Send all reports at once to backend
    const result = await sendReport(target, method, count);
    
    if (result.success) {
        const { successful, failed } = result.data;
        addLogEntry(`✅ Completed: ${successful}/${count} successful, ${failed}/${count} failed`, 'success');
        showResults(count, successful, failed);
    } else {
        addLogEntry(`❌ Report failed: ${result.error}`, 'error');
        showResults(count, 0, count);
    }
    
    reportingActive = false;
}

async function startBulkReport() {
    const method = document.getElementById('bulkMethod').value;
    const targetsText = document.getElementById('bulkTargets').value.trim();
    
    if (!targetsText) {
        alert('Please enter at least one username');
        return;
    }
    
    // Check user premium status first
    let userRole = null;
    let isPremium = false;
    try {
        const profileResponse = await apiCall('/v2/user/profile', { method: 'GET' });
        if (profileResponse.ok) {
            const profileData = await profileResponse.json();
            userRole = profileData.role;
            isPremium = profileData.isPremium;
            
            // Only allow users with active premium or admin/owner roles
            if (userRole !== 'admin' && userRole !== 'owner' && !isPremium) {
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
        console.error('Error checking user status:', error);
        alert('Error verifying account status. Please try again.');
        return;
    }
    
    const targets = targetsText.split('\n').filter(t => t.trim()).map(t => t.trim().replace('@', ''));
    
    if (targets.length === 0) {
        showError('No valid targets found');
        return;
    }
    
    const maxTargets = ['admin', 'owner'].includes(userRole) ? 500 : 200;
    if (targets.length > maxTargets) {
        showError(`Maximum ${maxTargets} targets allowed`);
        return;
    }
    
    showProgressSection();
    reportingActive = true;
    reportingAborted = false;
    
    addLogEntry(`🚀 Starting bulk report for ${targets.length} targets with method: ${method}`, 'info');
    addLogEntry(`⏱️  2-second delay between each target`, 'info');
    
    try {
        // Call the bulk reporting endpoint
        const response = await apiCall('/v2/reports/bulk', {
            method: 'POST',
            body: JSON.stringify({
                targets: targets,
                method: method
            })
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Bulk report failed');
        }
        
        const data = await response.json();
        const results = data.results;
        
        // Display results
        addLogEntry(`✅ Bulk report completed!`, 'success');
        addLogEntry(`📊 Total: ${results.total} | Success: ${results.successful} | Failed: ${results.failed} | Blacklisted: ${results.blacklisted}`, 'info');
        
        // Show individual results
        results.details.forEach((detail, index) => {
            if (detail.status === 'success') {
                addLogEntry(`✅ [${index + 1}/${results.total}] ${detail.target} - ${detail.message}`, 'success');
            } else if (detail.status === 'blacklisted') {
                addLogEntry(`⛔ [${index + 1}/${results.total}] ${detail.target} - ${detail.message}`, 'warning');
            } else {
                addLogEntry(`❌ [${index + 1}/${results.total}] ${detail.target} - ${detail.message}`, 'error');
            }
        });
        
        showResults(results.total, results.successful, results.failed);
        
    } catch (error) {
        console.error('Bulk report error:', error);
        addLogEntry(`❌ Bulk report failed: ${error.message}`, 'error');
        alert(`Bulk report failed: ${error.message}`);
    }
    
    reportingActive = false;
}

async function startMassReport() {
    const target = document.getElementById('massTarget').value.trim().replace('@', '');
    const count = parseInt(document.getElementById('massCount').value);
    const method = document.getElementById('massMethod').value;
    
    if (!target) {
        alert('Please enter a target username');
        return;
    }
    
    if (count < 1 || count > 200) {
        alert('Number of reports must be between 1 and 200');
        return;
    }
    
    // Check user premium status first - PREMIUM ONLY
    try {
        const profileResponse = await apiCall('/v2/user/profile', { method: 'GET' });
        if (profileResponse.ok) {
            const profileData = await profileResponse.json();
            const userRole = profileData.role;
            const isPremium = profileData.isPremium;
            
            // Only allow users with active premium or admin/owner roles
            if (userRole !== 'admin' && userRole !== 'owner' && !isPremium) {
                alert('❌ Mass Reporting is a Premium Feature!\n\n' +
                      'Mass reporting is exclusive to Premium users.\n\n' +
                      'Upgrade to Premium to:\n' +
                      '⚡ Report same user up to 200 times\n' +
                      '⚡ Multi-threaded ultra-fast reporting\n' +
                      '⚡ Unlimited daily reports\n' +
                      '⚡ Priority support\n\n' +
                      'Contact SWATNFO or Xefi for payment to upgrade your account.');
                return;
            }
        }
    } catch (error) {
        console.error('Error checking user status:', error);
        alert('Error verifying account status. Please try again.');
        return;
    }
    
    if (!confirm(`⚡ Mass Report Confirmation\n\nThis will send ${count} reports to @${target} using multi-threading.\n\nAll reports will be sent in parallel for maximum speed.\n\nContinue?`)) {
        return;
    }
    
    showProgressSection();
    reportingActive = true;
    reportingAborted = false;
    
    document.getElementById('currentTarget').textContent = `@${target}`;
    document.getElementById('progressText').textContent = `Processing...`;
    document.getElementById('successCount').textContent = '0';
    document.getElementById('failCount').textContent = '0';
    
    addLogEntry(`🚀 Starting mass report for @${target} x${count} times`, 'info');
    addLogEntry(`⚡ Using multi-threading with 10 concurrent workers`, 'info');
    addLogEntry(`📤 Sending all ${count} reports in parallel...`, 'info');
    addLogEntry(`⏳ Please wait while reports are processed on the server...`, 'warning');
    
    // Show animated progress bar
    let progress = 0;
    const progressInterval = setInterval(() => {
        progress += 2;
        if (progress <= 90) {
            document.getElementById('progressBar').style.width = progress + '%';
            document.getElementById('progressText').textContent = `Processing ${Math.floor(progress)}%...`;
        }
    }, 100);
    
    try {
        // Call the mass reporting endpoint
        const response = await apiCall('/v2/reports/mass', {
            method: 'POST',
            body: JSON.stringify({
                target: target,
                count: count,
                method: method
            })
        });
        
        clearInterval(progressInterval);
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Mass report failed');
        }
        
        const data = await response.json();
        
        // Display results
        addLogEntry(`✅ Mass report completed!`, 'success');
        addLogEntry(`📊 Total: ${data.total} | Success: ${data.successful} | Failed: ${data.failed}`, 'info');
        addLogEntry(`⚡ All ${data.successful} reports sent successfully using parallel processing!`, 'success');
        
        if (data.failed > 0) {
            addLogEntry(`⚠️ ${data.failed} reports failed - check server logs for details`, 'warning');
        }
        
        document.getElementById('progressText').textContent = `${data.total}/${data.total}`;
        document.getElementById('successCount').textContent = data.successful;
        document.getElementById('failCount').textContent = data.failed;
        
        const progressPercent = 100;
        document.getElementById('progressBar').style.width = progressPercent + '%';
        
        showResults(data.total, data.successful, data.failed);
        
    } catch (error) {
        clearInterval(progressInterval);
        console.error('Mass report error:', error);
        addLogEntry(`❌ Mass report failed: ${error.message}`, 'error');
        alert(`Mass report failed: ${error.message}`);
    }
    
    reportingActive = false;
}

async function sendReport(target, method, count = 1) {
    try {
        const response = await apiCall('/v2/reports/send', {
            method: 'POST',
            body: JSON.stringify({
                target: target,
                method: method,
                count: count
            })
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            return { success: true, data: data };
        } else {
            // Log the full error for debugging
            console.error('Report failed:', {
                status: response.status,
                statusText: response.statusText,
                data: data
            });
            
            // Return detailed error message
            let errorMsg = data.message || data.detail || 'Unknown error';
            return { success: false, error: errorMsg };
        }
    } catch (error) {
        console.error('Report error:', error);
        return { success: false, error: 'Network error: ' + error.message };
    }
}

function updateProgress(target, current, total, success, failed) {
    document.getElementById('currentTarget').textContent = target;
    document.getElementById('progressText').textContent = `${current}/${total}`;
    document.getElementById('successCount').textContent = success;
    document.getElementById('failCount').textContent = failed;
    
    const percentage = (current / total) * 100;
    const progressBar = document.getElementById('progressBar');
    
    // Add updating class for pulse animation
    progressBar.classList.add('updating');
    
    // Update width with smooth transition
    progressBar.style.width = percentage + '%';
    progressBar.setAttribute('data-percentage', Math.round(percentage) + '%');
    
    // Remove updating class after animation
    setTimeout(() => {
        progressBar.classList.remove('updating');
    }, 600);
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

// Scheduled Reports Functions
async function loadScheduledReports() {
    try {
        const response = await apiCall('/v2/reports/scheduled', { method: 'GET' });
        
        if (!response.ok) {
            throw new Error('Failed to load scheduled reports');
        }
        
        const data = await response.json();
        
        // Update limits display
        document.getElementById('scheduledCount').textContent = data.pendingCount || 0;
        document.getElementById('maxScheduled').textContent = data.maxScheduled || 3;
        
        // Display scheduled reports
        const listContainer = document.getElementById('scheduledReportsList');
        
        if (!data.scheduled || data.scheduled.length === 0) {
            listContainer.innerHTML = '<p class="empty-state">No scheduled reports yet</p>';
            return;
        }
        
        listContainer.innerHTML = data.scheduled.map(report => {
            const scheduleDate = new Date(report.scheduleTime);
            const targets = JSON.parse(report.targets);
            const targetsList = targets.slice(0, 5).map(t => `@${t}`).join(', ');
            const moreTargets = targets.length > 5 ? ` +${targets.length - 5} more` : '';
            
            const statusClass = report.status === 'pending' ? 'status-pending' : 
                               report.status === 'completed' ? 'status-completed' : 'status-failed';
            
            return `
                <div class="scheduled-item">
                    <div class="scheduled-item-header">
                        <div class="scheduled-info">
                            <div class="scheduled-time">⏰ ${scheduleDate.toLocaleString()}</div>
                            <div class="scheduled-method">Method: ${formatMethod(report.method)}</div>
                        </div>
                        <span class="scheduled-status ${statusClass}">${report.status}</span>
                    </div>
                    
                    <div class="scheduled-targets">
                        <div class="targets-header">Targets (${targets.length})</div>
                        <div class="targets-list">${targetsList}${moreTargets}</div>
                    </div>
                    
                    ${report.status === 'pending' ? `
                        <div class="scheduled-actions">
                            <button class="btn btn-small btn-cancel" onclick="cancelScheduledReport('${report.id}')">
                                ❌ Cancel
                            </button>
                        </div>
                    ` : ''}
                </div>
            `;
        }).join('');
        
    } catch (error) {
        console.error('Error loading scheduled reports:', error);
        alert('Failed to load scheduled reports: ' + error.message);
    }
}

async function createScheduledReport() {
    const targetsText = document.getElementById('scheduleTargets').value.trim();
    const method = document.getElementById('scheduleMethod').value;
    const scheduleDateTime = document.getElementById('scheduleDateTime').value;
    
    if (!targetsText) {
        alert('Please enter at least one username');
        return;
    }
    
    if (!scheduleDateTime) {
        alert('Please select a date and time');
        return;
    }
    
    const targets = targetsText.split('\n').filter(t => t.trim()).map(t => t.trim().replace('@', ''));
    
    if (targets.length === 0) {
        alert('No valid targets found');
        return;
    }
    
    // Convert to ISO format
    const scheduleTime = new Date(scheduleDateTime).toISOString();
    
    // Check if time is in the future
    if (new Date(scheduleTime) <= new Date()) {
        alert('Schedule time must be in the future');
        return;
    }
    
    try {
        const response = await apiCall('/v2/reports/schedule', {
            method: 'POST',
            body: JSON.stringify({
                targets: targets,
                method: method,
                scheduleTime: scheduleTime
            })
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to create scheduled report');
        }
        
        const data = await response.json();
        
        alert(`✅ Report scheduled successfully!\n\nSchedule ID: ${data.scheduledId}\nTargets: ${targets.length}\nTime: ${new Date(scheduleTime).toLocaleString()}`);
        
        // Clear form
        document.getElementById('scheduleTargets').value = '';
        document.getElementById('scheduleDateTime').value = '';
        
        // Reload scheduled reports
        await loadScheduledReports();
        
    } catch (error) {
        console.error('Error creating scheduled report:', error);
        alert('Failed to schedule report: ' + error.message);
    }
}

async function cancelScheduledReport(scheduleId) {
    if (!confirm('Are you sure you want to cancel this scheduled report?')) {
        return;
    }
    
    try {
        const response = await apiCall(`/v2/reports/scheduled/${scheduleId}`, {
            method: 'DELETE'
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to cancel scheduled report');
        }
        
        alert('✅ Scheduled report cancelled successfully');
        
        // Reload scheduled reports
        await loadScheduledReports();
        
    } catch (error) {
        console.error('Error cancelling scheduled report:', error);
        alert('Failed to cancel scheduled report: ' + error.message);
    }
}

function formatMethod(method) {
    const methodMap = {
        'spam': '💬 Spam',
        'self_injury': '🩹 Self Injury',
        'violent_threat': '⚔️ Violent Threat',
        'hate_speech': '🚫 Hate Speech',
        'nudity': '🔞 Nudity',
        'bullying': '😢 Bullying',
        'impersonation_me': '🎭 Impersonation (Me)',
        'sale_illegal': '💊 Sale of Illegal Goods',
        'violence': '🔪 Violence',
        'intellectual_property': '©️ Intellectual Property'
    };
    return methodMap[method] || method;
}

