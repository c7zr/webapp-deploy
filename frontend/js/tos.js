// TOS Page JavaScript
document.addEventListener('DOMContentLoaded', async () => {
    // Check if user is logged in
    const token = localStorage.getItem('token');
    
    if (token) {
        // User is logged in - load profile
        await loadUserProfile();
        setupProfileDropdown();
        
        // Setup logout button
        const logoutBtn = document.getElementById('logout-btn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', (e) => {
                e.preventDefault();
                logout();
            });
        }
    } else {
        // User is not logged in - hide profile dropdown, show login link
        const profileDropdown = document.getElementById('profileDropdown');
        if (profileDropdown) {
            profileDropdown.innerHTML = '<a href="login.html" style="color: #8a2be2; font-weight: 600; padding: 10px 20px; border: 2px solid #8a2be2; border-radius: 8px; transition: all 0.3s ease;">Login</a>';
        }
    }

    // Smooth scroll for internal links
    setupSmoothScroll();

    // Add intersection observer for scroll animations
    setupScrollAnimations();
});

async function loadUserProfile() {
    try {
        const response = await fetch(`${API_BASE_URL}/v2/user/profile`, {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            }
        });

        if (!response.ok) {
            throw new Error('Failed to load profile');
        }

        const data = await response.json();
        
        // Update profile UI
        const profileName = document.getElementById('profileName');
        const profileAvatar = document.getElementById('profileAvatar');
        const dropdownUsername = document.getElementById('dropdownUsername');
        const dropdownRole = document.getElementById('dropdownRole');
        
        if (profileName) profileName.textContent = data.username;
        if (profileAvatar) profileAvatar.textContent = data.username.charAt(0).toUpperCase();
        if (dropdownUsername) dropdownUsername.textContent = data.username;
        if (dropdownRole) {
            dropdownRole.textContent = data.role;
            dropdownRole.className = `role role-${data.role.toLowerCase()}`;
        }
    } catch (error) {
        console.error('Error loading profile:', error);
        // If profile fails, still allow access to TOS
    }
}

function setupProfileDropdown() {
    const profileButton = document.getElementById('profileButton');
    const dropdown = document.getElementById('profileDropdown');
    
    if (profileButton && dropdown) {
        profileButton.addEventListener('click', (e) => {
            e.stopPropagation();
            dropdown.classList.toggle('active');
        });

        // Close dropdown when clicking outside
        document.addEventListener('click', (e) => {
            if (!dropdown.contains(e.target)) {
                dropdown.classList.remove('active');
            }
        });
    }
}

function logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('username');
    localStorage.removeItem('loginTime');
    window.location.href = 'login.html';
}

function setupSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
}

function setupScrollAnimations() {
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
            }
        });
    }, {
        threshold: 0.1,
        rootMargin: '0px 0px -100px 0px'
    });

    // Observe all sections
    document.querySelectorAll('.tos-section').forEach(section => {
        observer.observe(section);
    });
}

// Add visible class animation
const style = document.createElement('style');
style.textContent = `
    .tos-section.visible {
        animation: fadeInUp 0.6s ease-out forwards;
    }
    
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(30px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
`;
document.head.appendChild(style);

// Print TOS function (optional)
function printTOS() {
    window.print();
}

// Copy section link function (optional)
function copySectionLink(sectionId) {
    const url = `${window.location.origin}${window.location.pathname}#${sectionId}`;
    navigator.clipboard.writeText(url).then(() => {
        showNotification('Section link copied to clipboard!');
    });
}

function showNotification(message) {
    const notification = document.createElement('div');
    notification.className = 'notification';
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        bottom: 30px;
        right: 30px;
        background: linear-gradient(135deg, #8a2be2, #ff6b9d);
        color: white;
        padding: 15px 25px;
        border-radius: 10px;
        box-shadow: 0 10px 30px rgba(138, 43, 226, 0.3);
        z-index: 10000;
        animation: slideIn 0.3s ease-out;
    `;

    document.body.appendChild(notification);

    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Add notification animations
const notificationStyle = document.createElement('style');
notificationStyle.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(400px);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(400px);
            opacity: 0;
        }
    }
`;
document.head.appendChild(notificationStyle);
