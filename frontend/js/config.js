// API Configuration
const API_BASE_URL = 'http://localhost:8000';

// Helper function to get auth token
function getAuthToken() {
    return localStorage.getItem('token') || sessionStorage.getItem('token');
}

// Helper function to make authenticated API calls
async function apiCall(endpoint, options = {}) {
    const token = getAuthToken();
    
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers
    };
    
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        ...options,
        headers
    });
    
    return response;
}

// Check if user is logged in
function isLoggedIn() {
    return !!getAuthToken();
}

// Redirect to login if not authenticated
async function requireAuth() {
    if (!isLoggedIn()) {
        window.location.href = '/login';
        return false;
    }
    
    // Verify token is still valid and get user data
    try {
        const response = await apiCall('/v2/user/profile', { method: 'GET' });
        if (!response.ok) {
            // Token invalid or expired
            localStorage.removeItem('token');
            sessionStorage.removeItem('token');
            localStorage.removeItem('user');
            window.location.href = '/login';
            return false;
        }
        
        // Update user data in localStorage
        const userData = await response.json();
        localStorage.setItem('user', JSON.stringify(userData));
        
        return true;
    } catch (error) {
        console.error('Auth verification failed:', error);
        window.location.href = '/login';
        return false;
    }
}

// Logout function
function logout() {
    localStorage.removeItem('token');
    sessionStorage.removeItem('token');
    localStorage.removeItem('user');
    window.location.href = '/login';
}

// Initialize profile dropdown
function initProfileDropdown() {
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    const profileButton = document.getElementById('profileButton');
    const profileDropdown = document.getElementById('profileDropdown');
    const profileName = document.getElementById('profileName');
    const profileAvatar = document.getElementById('profileAvatar');
    const dropdownUsername = document.getElementById('dropdownUsername');
    const dropdownRole = document.getElementById('dropdownRole');
    
    // Check if required elements exist
    if (!profileButton || !profileDropdown) {
        console.error('Profile elements not found');
        return;
    }
    
    if (user.username) {
        // Set profile info
        if (profileName) profileName.textContent = user.username;
        if (profileAvatar) profileAvatar.textContent = user.username.charAt(0).toUpperCase();
        if (dropdownUsername) dropdownUsername.textContent = user.username;
        if (dropdownRole) dropdownRole.textContent = user.role || 'user';
        
        // Hide admin link if not admin/owner
        const adminLink = document.getElementById('adminLink');
        if (adminLink) {
            if (user.role === 'admin' || user.role === 'owner') {
                adminLink.style.display = 'flex';
            } else {
                adminLink.style.display = 'none';
            }
        }
    }
    
    // Toggle dropdown
    profileButton.addEventListener('click', (e) => {
        e.stopPropagation();
        profileDropdown.classList.toggle('active');
    });
    
    // Close dropdown when clicking outside
    document.addEventListener('click', (e) => {
        if (!profileDropdown.contains(e.target)) {
            profileDropdown.classList.remove('active');
        }
    });
}

// Input sanitization to prevent XSS
function sanitizeInput(input) {
    const div = document.createElement('div');
    div.textContent = input;
    return div.innerHTML;
}

// Validate email format
function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

// Password strength checker
function checkPasswordStrength(password) {
    const checks = {
        length: password.length >= 8,
        uppercase: /[A-Z]/.test(password),
        lowercase: /[a-z]/.test(password),
        number: /[0-9]/.test(password),
        special: /[!@#$%^&*(),.?":{}|<>]/.test(password)
    };
    
    const passed = Object.values(checks).filter(v => v).length;
    
    return {
        checks,
        strength: passed < 3 ? 'weak' : passed < 4 ? 'medium' : 'strong',
        score: passed
    };
}

