// Login Form Handler
document.addEventListener('DOMContentLoaded', () => {
    // Redirect if already logged in
    if (isLoggedIn()) {
        window.location.href = '/dashboard';
        return;
    }
    
    const loginForm = document.getElementById('loginForm');
    const usernameInput = document.getElementById('username');
    const passwordInput = document.getElementById('password');
    const rememberCheckbox = document.getElementById('remember');

    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const username = usernameInput.value.trim();
        const password = passwordInput.value;
        const remember = rememberCheckbox.checked;

        if (!username || !password) {
            showError('Please fill in all fields');
            loginForm.classList.add('shake');
            setTimeout(() => loginForm.classList.remove('shake'), 300);
            return;
        }

        try {
            const response = await apiCall('/v2/auth/login', {
                method: 'POST',
                body: JSON.stringify({
                    username: username,
                    password: password,
                    remember: remember
                })
            });

            const data = await response.json();

            if (response.ok) {
                // Store JWT token with expiry tracking
                setAuthToken(data.token, remember);
                
                // Store user data
                localStorage.setItem('user', JSON.stringify(data.user));
                
                // Redirect to dashboard
                window.location.href = '/dashboard';
            } else {
                showError(data.message || 'Login failed');
                loginForm.classList.add('shake');
                setTimeout(() => loginForm.classList.remove('shake'), 300);
            }
        } catch (error) {
            console.error('Login error:', error);
            showError('Connection error. Please try again.');
            loginForm.classList.add('shake');
            setTimeout(() => loginForm.classList.remove('shake'), 300);
        }
    });

    function showError(message) {
        // Remove existing error if any
        const existingError = document.querySelector('.error-message');
        if (existingError) {
            existingError.remove();
        }

        // Create error message
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.style.cssText = `
            background-color: rgba(231, 76, 60, 0.2);
            border: 1px solid #e74c3c;
            color: #e74c3c;
            padding: 12px;
            border-radius: 6px;
            margin-bottom: 15px;
            text-align: center;
        `;
        errorDiv.textContent = message;

        loginForm.insertBefore(errorDiv, loginForm.firstChild);

        // Remove error after 3 seconds
        setTimeout(() => {
            errorDiv.style.opacity = '0';
            errorDiv.style.transition = 'opacity 0.3s ease';
            setTimeout(() => errorDiv.remove(), 300);
        }, 3000);
    }
});

