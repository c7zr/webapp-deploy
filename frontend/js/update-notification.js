// Update Notification System
// Automatically shows update notifications on all pages

(function() {
    'use strict';
    
    const LATEST_VERSION = 'v2.5.0';
    const UPDATE_DATE = 'December 1, 2025';
    const STORAGE_KEY = 'swatnfo_update_dismissed';
    
    // Check if user has already dismissed this update
    const dismissedVersion = localStorage.getItem(STORAGE_KEY);
    if (dismissedVersion === LATEST_VERSION) {
        return; // Don't show notification if already dismissed
    }
    
    // Create and inject notification banner
    function showUpdateNotification() {
        // Don't show on login/register pages
        if (window.location.pathname.includes('login') || window.location.pathname.includes('register')) {
            return;
        }
        
        const banner = document.createElement('div');
        banner.id = 'updateNotificationBanner';
        banner.innerHTML = `
            <div class="update-notification-content">
                <div class="update-icon">🚀</div>
                <div class="update-text">
                    <strong>New Update Available: ${LATEST_VERSION}</strong>
                    <span>Instagram API Dec 2025 + Updates Page - ${UPDATE_DATE}</span>
                </div>
                <div class="update-actions">
                    <a href="/updates.html" class="update-btn update-btn-primary">View Changes</a>
                    <button class="update-btn update-btn-dismiss" onclick="dismissUpdateNotification()">Dismiss</button>
                </div>
            </div>
        `;
        
        // Add styles
        const style = document.createElement('style');
        style.textContent = `
            #updateNotificationBanner {
                position: fixed;
                top: 70px;
                left: 50%;
                transform: translateX(-50%);
                z-index: 9999;
                width: calc(100% - 2rem);
                max-width: 900px;
                background: linear-gradient(135deg, rgba(147, 51, 234, 0.95), rgba(126, 34, 206, 0.95));
                backdrop-filter: blur(10px);
                border: 2px solid rgba(147, 51, 234, 0.5);
                border-radius: 16px;
                padding: 1.25rem;
                box-shadow: 0 10px 40px rgba(147, 51, 234, 0.4);
                animation: slideDown 0.5s ease-out, pulse 2s ease-in-out infinite;
            }
            
            @keyframes slideDown {
                from {
                    opacity: 0;
                    transform: translate(-50%, -20px);
                }
                to {
                    opacity: 1;
                    transform: translate(-50%, 0);
                }
            }
            
            @keyframes pulse {
                0%, 100% {
                    box-shadow: 0 10px 40px rgba(147, 51, 234, 0.4);
                }
                50% {
                    box-shadow: 0 10px 50px rgba(147, 51, 234, 0.6);
                }
            }
            
            .update-notification-content {
                display: flex;
                align-items: center;
                gap: 1rem;
                color: white;
            }
            
            .update-icon {
                font-size: 2rem;
                animation: bounce 2s ease-in-out infinite;
            }
            
            @keyframes bounce {
                0%, 100% {
                    transform: translateY(0);
                }
                50% {
                    transform: translateY(-10px);
                }
            }
            
            .update-text {
                flex: 1;
                display: flex;
                flex-direction: column;
                gap: 0.25rem;
            }
            
            .update-text strong {
                font-size: 1.1rem;
                font-weight: 700;
            }
            
            .update-text span {
                font-size: 0.9rem;
                opacity: 0.9;
            }
            
            .update-actions {
                display: flex;
                gap: 0.75rem;
            }
            
            .update-btn {
                padding: 0.6rem 1.25rem;
                border-radius: 8px;
                font-weight: 600;
                font-size: 0.95rem;
                cursor: pointer;
                transition: all 0.3s ease;
                text-decoration: none;
                border: none;
                white-space: nowrap;
            }
            
            .update-btn-primary {
                background: white;
                color: #9333ea;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
            }
            
            .update-btn-primary:hover {
                transform: translateY(-2px);
                box-shadow: 0 6px 16px rgba(0, 0, 0, 0.3);
            }
            
            .update-btn-dismiss {
                background: rgba(255, 255, 255, 0.15);
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.3);
            }
            
            .update-btn-dismiss:hover {
                background: rgba(255, 255, 255, 0.25);
            }
            
            @media (max-width: 768px) {
                #updateNotificationBanner {
                    top: 60px;
                    width: calc(100% - 1rem);
                    padding: 1rem;
                }
                
                .update-notification-content {
                    flex-direction: column;
                    text-align: center;
                }
                
                .update-icon {
                    font-size: 1.5rem;
                }
                
                .update-text strong {
                    font-size: 1rem;
                }
                
                .update-text span {
                    font-size: 0.85rem;
                }
                
                .update-actions {
                    flex-direction: column;
                    width: 100%;
                }
                
                .update-btn {
                    width: 100%;
                    text-align: center;
                }
            }
        `;
        
        document.head.appendChild(style);
        document.body.appendChild(banner);
    }
    
    // Dismiss notification function
    window.dismissUpdateNotification = function() {
        const banner = document.getElementById('updateNotificationBanner');
        if (banner) {
            banner.style.animation = 'slideDown 0.3s ease-out reverse';
            setTimeout(() => {
                banner.remove();
            }, 300);
        }
        localStorage.setItem(STORAGE_KEY, LATEST_VERSION);
    };
    
    // Show notification when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', showUpdateNotification);
    } else {
        showUpdateNotification();
    }
})();
