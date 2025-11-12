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
    
    // Show premium badge if user has premium
    if (user.premium) {
        const premiumBadge = document.getElementById('premiumBadge');
        if (premiumBadge) {
            premiumBadge.style.display = 'flex';
        }
    }
}

async function loadStats() {
    try {
        const response = await apiCall('/v2/reports/stats', {
            method: 'GET'
        });

        if (response.ok) {
            const data = await response.json();
            const total = data.total || 0;
            const successful = data.successful || 0;
            const failed = data.failed || 0;
            const targets = data.targets || 0;
            
            // Animate the numbers
            animateValue('totalReports', 0, total, 1000);
            animateValue('successfulReports', 0, successful, 1200);
            animateValue('failedReports', 0, failed, 1400);
            animateValue('targetsReported', 0, targets, 1600);
            
            // Calculate and display success rate
            if (total > 0) {
                const successRate = Math.round((successful / total) * 100);
                const successRateEl = document.getElementById('successRate');
                if (successRateEl) {
                    successRateEl.textContent = `${successRate}% success rate`;
                }
            }
        }
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

function animateValue(id, start, end, duration) {
    const element = document.getElementById(id);
    if (!element) return;
    
    const range = end - start;
    const increment = range / (duration / 16); // 60 FPS
    let current = start;
    
    const timer = setInterval(() => {
        current += increment;
        if ((increment > 0 && current >= end) || (increment < 0 && current <= end)) {
            current = end;
            clearInterval(timer);
        }
        element.textContent = Math.floor(current).toLocaleString();
    }, 16);
}

async function loadRecentActivity() {
    try {
        const response = await apiCall('/v2/reports/recent?limit=5', {
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
            <div class="activity-loading">
                <p style="color: rgba(255, 255, 255, 0.5);">No recent activity yet. Start reporting to see your activity here!</p>
            </div>
        `;
        return;
    }

    activityList.innerHTML = reports.map((report, index) => {
        const isSuccess = report.status === 'success';
        const isPending = report.status === 'pending';
        const iconClass = isSuccess ? 'success' : isPending ? 'pending' : 'failed';
        const statusText = isSuccess ? 'Successful' : isPending ? 'Pending' : 'Failed';
        const icon = isSuccess ? '✓' : isPending ? '⏱' : '✕';
        
        return `
            <div class="activity-item" style="animation: fadeInUp 0.4s ease-out ${index * 0.1}s backwards">
                <div class="activity-icon ${iconClass}">
                    ${icon}
                </div>
                <div class="activity-details">
                    <div class="activity-target">@${report.target}</div>
                    <div class="activity-meta">${report.method} • ${report.type} • ${formatTime(report.timestamp)}</div>
                </div>
                <div class="activity-status ${iconClass}">
                    ${statusText}
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


