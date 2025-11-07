// Dashboard Handler
document.addEventListener('DOMContentLoaded', async () => {
    await requireAuth();
    initProfileDropdown();
    loadUserData();
    loadStats();
    loadRecentActivity();
});

function loadUserData() {
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    if (user.username) {
        document.getElementById('username').textContent = user.username;
    }
}

async function loadStats() {
    try {
        const response = await apiCall('/v2/reports/stats', {
            method: 'GET'
        });

        if (response.ok) {
            const data = await response.json();
            document.getElementById('totalReports').textContent = data.total || 0;
            document.getElementById('successfulReports').textContent = data.successful || 0;
            document.getElementById('failedReports').textContent = data.failed || 0;
            document.getElementById('targetsReported').textContent = data.targets || 0;
        }
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

async function loadRecentActivity() {
    try {
        const response = await apiCall('/v2/reports/recent?limit=10', {
            method: 'GET'
        });

        if (response.ok) {
            const data = await response.json();
            displayActivity(data.reports || []);
        }
    } catch (error) {
        console.error('Error loading recent activity:', error);
        displayActivity([]);
    }
}

function displayActivity(reports) {
    const activityList = document.getElementById('activityList');
    
    if (reports.length === 0) {
        activityList.innerHTML = `
            <div style="text-align: center; color: var(--text-gray); padding: 20px;">
                No recent activity
            </div>
        `;
        return;
    }

    activityList.innerHTML = reports.map(report => {
        const statusColor = report.status === 'success' ? '#2ecc71' : '#e74c3c';
        const statusIcon = report.status === 'success' ? '✅' : '❌';
        
        return `
            <div class="activity-item">
                <div class="activity-info">
                    <strong style="color: var(--purple);">${statusIcon} ${report.target}</strong>
                    <p>Method: ${report.method} | Type: ${report.type}</p>
                </div>
                <div class="activity-time">
                    ${formatTime(report.timestamp)}
                </div>
            </div>
        `;
    }).join('');
}

function formatTime(timestamp) {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = Math.floor((now - date) / 1000); // seconds

    if (diff < 60) return 'Just now';
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return `${Math.floor(diff / 86400)}d ago`;
}

