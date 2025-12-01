console.log('config.js loaded, isLoggedIn:', typeof isLoggedIn);
// API Configuration
const API_BASE_URL = window.location.origin;

// Helper function to get auth token
function getAuthToken() {
    // Check localStorage first (remember me)
    const localToken = localStorage.getItem('token');
    if (localToken) {
        // Check if token has expired
        const tokenExpiry = localStorage.getItem('token_expiry');
        if (tokenExpiry && new Date().getTime() > parseInt(tokenExpiry)) {
            // Token expired, clear it
            localStorage.removeItem('token');
            localStorage.removeItem('token_expiry');
            localStorage.removeItem('user');
            return null;
        }
        return localToken;
    }
    
    // Check sessionStorage (don't remember me)
    return sessionStorage.getItem('token');
}

// Helper function to set auth token with expiry
function setAuthToken(token, remember, expiryDays = 7) {
    if (remember) {
        localStorage.setItem('token', token);
        // Set expiry timestamp (7 days from now)
        const expiryTime = new Date().getTime() + (expiryDays * 24 * 60 * 60 * 1000);
        localStorage.setItem('token_expiry', expiryTime.toString());
    } else {
        sessionStorage.setItem('token', token);
    }
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
    
    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            ...options,
            headers
        });
        
        return response;
    } catch (error) {
        console.error('API call failed:', endpoint, error);
        throw new Error('Network error. Please check your connection.');
    }
}

// Show user-friendly error notification
function showError(message, duration = 5000) {
    // Remove existing error if present
    const existing = document.querySelector('.error-toast');
    if (existing) existing.remove();
    
    const toast = document.createElement('div');
    toast.className = 'error-toast';
    toast.innerHTML = `
        <div class="toast-icon">❌</div>
        <div class="toast-message">${sanitizeInput(message)}</div>
        <button class="toast-close" onclick="this.parentElement.remove()">✕</button>
    `;
    
    document.body.appendChild(toast);
    
    // Auto-remove after duration
    setTimeout(() => {
        if (toast.parentElement) {
            toast.classList.add('toast-fade-out');
            setTimeout(() => toast.remove(), 300);
        }
    }, duration);
}

// Show success notification
function showSuccess(message, duration = 3000) {
    const existing = document.querySelector('.success-toast');
    if (existing) existing.remove();
    
    const toast = document.createElement('div');
    toast.className = 'success-toast';
    toast.innerHTML = `
        <div class="toast-icon">✅</div>
        <div class="toast-message">${sanitizeInput(message)}</div>
        <button class="toast-close" onclick="this.parentElement.remove()">✕</button>
    `;
    
    document.body.appendChild(toast);
    
    setTimeout(() => {
        if (toast.parentElement) {
            toast.classList.add('toast-fade-out');
            setTimeout(() => toast.remove(), 300);
        }
    }, duration);
}

// Handle API errors with user-friendly messages
async function handleApiError(response, defaultMessage = 'An error occurred') {
    let errorMessage = defaultMessage;
    
    try {
        const data = await response.json();
        errorMessage = data.detail || data.message || errorMessage;
    } catch (e) {
        // If JSON parsing fails, use status text
        errorMessage = response.statusText || errorMessage;
    }
    
    // Map common HTTP errors to friendly messages
    const statusMessages = {
        400: 'Invalid request. Please check your input.',
        401: 'Session expired. Please log in again.',
        403: 'You don\'t have permission to do that.',
        404: 'Resource not found.',
        429: 'Too many requests. Please wait a moment.',
        500: 'Server error. Please try again later.',
        503: 'Service temporarily unavailable.'
    };
    
    if (statusMessages[response.status]) {
        errorMessage = statusMessages[response.status];
    }
    
    showError(errorMessage);
    return errorMessage;
}

// Check if user is logged in
function isLoggedIn() {
    return !!getAuthToken();
}

// Redirect to login if not authenticated
async function requireAuth() {
    const token = getAuthToken();
    
    if (!token) {
        console.log('No token found, redirecting to login');
        window.location.href = '/login';
        return false;
    }
    
    // Verify token is still valid and get user data
    try {
        const response = await apiCall('/v2/user/profile', { method: 'GET' });
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('Token verification failed:', response.status, errorText);
            
            // Only clear auth and redirect on actual auth errors
            if (response.status === 401 || response.status === 403) {
                localStorage.removeItem('token');
                localStorage.removeItem('token_expiry');
                sessionStorage.removeItem('token');
                localStorage.removeItem('user');
                window.location.href = '/login';
                return false;
            }
            
            // For other errors (500, network issues), don't log out immediately
            console.warn('Profile fetch failed but keeping user logged in');
            return true;
        }
        
        // Update user data in localStorage
        const userData = await response.json();
        localStorage.setItem('user', JSON.stringify(userData));
        
        return true;
    } catch (error) {
        console.error('Auth verification error:', error);
        // Don't log out on network errors, only on auth failures
        console.warn('Network error during auth check, keeping user logged in');
        return true;
    }
}

// Logout function
function logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('token_expiry');
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

