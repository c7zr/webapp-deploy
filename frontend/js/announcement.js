// Announcement System - November 2025 Update
function showAnnouncement() {
    // Only show if user is logged in
    const token = localStorage.getItem('token');
    if (!token) {
        return;
    }
    
    // Reset for new announcement - November 2025
    const announcementVersion = 'v2.1-nov2025';
    const hasSeenThisVersion = localStorage.getItem('announcementVersion') === announcementVersion;
    
    // Only show once per version
    if (hasSeenThisVersion) {
        return;
    }
    
    // Check if mobile device
    const isMobile = window.innerWidth <= 768;
    
    // Create modal HTML
    const modal = document.createElement('div');
    modal.id = 'announcementModal';
    modal.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.8);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 10000;
        animation: fadeIn 0.3s ease;
    `;
    
    modal.innerHTML = `
        <div style="
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            border: 2px solid #a855f7;
            border-radius: 16px;
            padding: 32px;
            max-width: 600px;
            max-height: 90vh;
            overflow-y: auto;
            width: 90%;
            box-shadow: 0 20px 60px rgba(168, 85, 247, 0.3);
            position: relative;
            animation: slideUp 0.4s ease;
        ">
            <button id="closeAnnouncement" style="
                position: absolute;
                top: 16px;
                right: 16px;
                background: transparent;
                border: none;
                color: #fff;
                font-size: 24px;
                cursor: pointer;
                width: 32px;
                height: 32px;
                display: flex;
                align-items: center;
                justify-content: center;
                border-radius: 50%;
                transition: all 0.3s;
            " onmouseover="this.style.background='rgba(168, 85, 247, 0.2)'" onmouseout="this.style.background='transparent'">×</button>
            
            <div style="text-align: center; margin-bottom: 24px;">
                <div style="
                    width: 80px;
                    height: 80px;
                    background: linear-gradient(135deg, #a855f7 0%, #8b5cf6 100%);
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    margin: 0 auto 16px;
                    font-size: 48px;
                    box-shadow: 0 8px 32px rgba(168, 85, 247, 0.4);
                ">🎉</div>
                <h2 style="
                    color: #fff;
                    font-size: 28px;
                    margin: 0 0 8px 0;
                    font-weight: 700;
                ">What's New!</h2>
                <p style="
                    color: #a0a0a0;
                    font-size: 14px;
                    margin: 0;
                ">We've completed major improvements and new features</p>
            </div>
            
            <div style="
                background: rgba(168, 85, 247, 0.1);
                border: 1px solid rgba(168, 85, 247, 0.3);
                border-radius: 12px;
                padding: 20px;
                margin-bottom: 16px;
            ">
                <h3 style="
                    color: #a855f7;
                    font-size: 18px;
                    margin: 0 0 12px 0;
                    display: flex;
                    align-items: center;
                    gap: 8px;
                ">
                    <span style="font-size: 22px;">⏰</span>
                    NEW: Scheduled Reports
                </h3>
                <p style="
                    color: #e0e0e0;
                    font-size: 15px;
                    line-height: 1.6;
                    margin: 0;
                ">
                    Schedule reports for any future time! <strong style="color: #a855f7;">Free: 3 max</strong> | <strong style="color: #a855f7;">Premium: 50 max</strong> with auto-execution!
                </p>
            </div>
            
            <div style="
                background: rgba(168, 85, 247, 0.1);
                border: 1px solid rgba(168, 85, 247, 0.3);
                border-radius: 12px;
                padding: 20px;
                margin-bottom: 16px;
            ">
                <h3 style="
                    color: #a855f7;
                    font-size: 18px;
                    margin: 0 0 12px 0;
                    display: flex;
                    align-items: center;
                    gap: 8px;
                ">
                    <span style="font-size: 22px;">🚀</span>
                    Instagram Updates
                </h3>
                <p style="
                    color: #e0e0e0;
                    font-size: 15px;
                    line-height: 1.6;
                    margin: 0;
                ">
                    Updated to <strong style="color: #a855f7;">Instagram 320.0+</strong> with iPhone 15 Pro user agents! Premium users get <strong style="color: #a855f7;">better bypasses & faster success rates</strong>!
                </p>
            </div>
            
            <div style="
                background: rgba(168, 85, 247, 0.1);
                border: 1px solid rgba(168, 85, 247, 0.3);
                border-radius: 12px;
                padding: 20px;
                margin-bottom: 24px;
            ">
                <h3 style="
                    color: #a855f7;
                    font-size: 18px;
                    margin: 0 0 12px 0;
                    display: flex;
                    align-items: center;
                    gap: 8px;
                ">
                    <span style="font-size: 22px;">⚡</span>
                    Performance Boost
                </h3>
                <p style="
                    color: #e0e0e0;
                    font-size: 15px;
                    line-height: 1.6;
                    margin: 0;
                ">
                    Mass reporting uses <strong style="color: #a855f7;">20 concurrent threads</strong> for ultra-fast execution. 200 reports in ~10 seconds!
                </p>
            </div>
            
            <button id="gotItBtn" style="
                background: linear-gradient(135deg, #a855f7 0%, #8b5cf6 100%);
                color: white;
                border: none;
                padding: 14px 32px;
                border-radius: 8px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                width: 100%;
                transition: all 0.3s;
                box-shadow: 0 4px 16px rgba(168, 85, 247, 0.4);
            " onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 6px 24px rgba(168, 85, 247, 0.6)'"
               onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 16px rgba(168, 85, 247, 0.4)'">
                Got it! Let's go 🚀
            </button>
            
            <p style="
                color: #808080;
                font-size: 12px;
                text-align: center;
                margin: 16px 0 0 0;
            ">Auto-closing in 3 seconds...</p>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    // Add animations
    const style = document.createElement('style');
    style.textContent = `
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
        @keyframes slideUp {
            from { transform: translateY(30px); opacity: 0; }
            to { transform: translateY(0); opacity: 1; }
        }
    `;
    document.head.appendChild(style);
    
    // Close handlers
    function closeModal() {
        modal.style.animation = 'fadeOut 0.3s ease';
        setTimeout(() => {
            modal.remove();
            style.remove();
        }, 300);
        
        // Mark this version as seen
        localStorage.setItem('announcementVersion', announcementVersion);
        // Keep old key for compatibility
        localStorage.setItem('announcementSeen', 'true');
    }
    
    document.getElementById('closeAnnouncement').addEventListener('click', closeModal);
    document.getElementById('gotItBtn').addEventListener('click', closeModal);
    
    // Close on outside click
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            closeModal();
        }
    });
    
    // Auto-close after 3 seconds
    setTimeout(closeModal, 3000);
}

// Show announcement after page loads
window.addEventListener('load', () => {
    setTimeout(showAnnouncement, 500);
});
