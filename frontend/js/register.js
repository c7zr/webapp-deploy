// Register Form Handler
document.addEventListener('DOMContentLoaded', () => {
    // Redirect if already logged in
    if (isLoggedIn()) {
        window.location.href = '/dashboard';
        return;
    }
    
    const registerForm = document.getElementById('registerForm');
    const usernameInput = document.getElementById('username');
    const emailInput = document.getElementById('email');
    const passwordInput = document.getElementById('password');
    const confirmPasswordInput = document.getElementById('confirmPassword');
    const termsCheckbox = document.getElementById('terms');
    
    // Password strength indicator
    const strengthIndicator = document.getElementById('passwordStrength');
    const strengthFill = document.getElementById('strengthFill');
    const strengthText = document.getElementById('strengthText');
    
    passwordInput.addEventListener('input', () => {
        const password = passwordInput.value;
        
        if (password.length === 0) {
            strengthIndicator.style.display = 'none';
            return;
        }
        
        strengthIndicator.style.display = 'block';
        const result = checkPasswordStrength(password);
        
        // Update bar
        strengthFill.className = 'strength-fill ' + result.strength;
        
        // Update text
        strengthText.className = 'strength-text ' + result.strength;
        strengthText.textContent = `Password strength: ${result.strength.charAt(0).toUpperCase() + result.strength.slice(1)}`;
        
        // Update requirements
        document.getElementById('req-length').className = result.checks.length ? 'met' : '';
        document.getElementById('req-uppercase').className = result.checks.uppercase ? 'met' : '';
        document.getElementById('req-lowercase').className = result.checks.lowercase ? 'met' : '';
        document.getElementById('req-number').className = result.checks.number ? 'met' : '';
    });

    registerForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const username = usernameInput.value.trim();
        const email = emailInput.value.trim();
        const password = passwordInput.value;
        const confirmPassword = confirmPasswordInput.value;
        const termsAccepted = termsCheckbox.checked;

        // Validation
        if (!username || !password || !confirmPassword) {
            showError('Please fill in username and password');
            registerForm.classList.add('shake');
            setTimeout(() => registerForm.classList.remove('shake'), 300);
            return;
        }

        if (username.length < 3) {
            showError('Username must be at least 3 characters');
            registerForm.classList.add('shake');
            setTimeout(() => registerForm.classList.remove('shake'), 300);
            return;
        }

        // Only validate email if provided
        if (email && !isValidEmail(email)) {
            showError('Please enter a valid email address');
            registerForm.classList.add('shake');
            setTimeout(() => registerForm.classList.remove('shake'), 300);
            return;
        }

        if (password.length < 8) {
            showError('Password must be at least 8 characters');
            registerForm.classList.add('shake');
            setTimeout(() => registerForm.classList.remove('shake'), 300);
            return;
        }

        if (password !== confirmPassword) {
            showError('Passwords do not match');
            registerForm.classList.add('shake');
            setTimeout(() => registerForm.classList.remove('shake'), 300);
            return;
        }

        if (!termsAccepted) {
            showError('Please accept the Terms of Service');
            registerForm.classList.add('shake');
            setTimeout(() => registerForm.classList.remove('shake'), 300);
            return;
        }

        try {
            const requestBody = {
                username: username,
                password: password
            };
            
            // Only include email if provided
            if (email) {
                requestBody.email = email;
            }
            
            const response = await apiCall('/v2/auth/register', {
                method: 'POST',
                body: JSON.stringify(requestBody)
            });

            const data = await response.json();

            if (response.ok) {
                showSuccess('Account created successfully! Redirecting to login...');
                setTimeout(() => {
                    window.location.href = '/login';
                }, 2000);
            } else {
                showError(data.detail || data.message || 'Registration failed');
                registerForm.classList.add('shake');
                setTimeout(() => registerForm.classList.remove('shake'), 300);
            }
        } catch (error) {
            console.error('Registration error:', error);
            showError('Connection error. Please try again.');
            registerForm.classList.add('shake');
            setTimeout(() => registerForm.classList.remove('shake'), 300);
        }
    });

    function isValidEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }

    function showError(message) {
        showMessage(message, 'error');
    }

    function showSuccess(message) {
        showMessage(message, 'success');
    }

    function showMessage(message, type) {
        // Remove existing message if any
        const existingMessage = document.querySelector('.message');
        if (existingMessage) {
            existingMessage.remove();
        }

        // Create message
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message';
        
        if (type === 'error') {
            messageDiv.style.cssText = `
                background-color: rgba(231, 76, 60, 0.2);
                border: 1px solid #e74c3c;
                color: #e74c3c;
                padding: 12px;
                border-radius: 6px;
                margin-bottom: 15px;
                text-align: center;
            `;
        } else if (type === 'success') {
            messageDiv.style.cssText = `
                background-color: rgba(46, 204, 113, 0.2);
                border: 1px solid #2ecc71;
                color: #2ecc71;
                padding: 12px;
                border-radius: 6px;
                margin-bottom: 15px;
                text-align: center;
            `;
        }
        
        messageDiv.textContent = message;
        registerForm.insertBefore(messageDiv, registerForm.firstChild);

        // Remove message after 3 seconds (unless it's a success message)
        if (type === 'error') {
            setTimeout(() => {
                messageDiv.style.opacity = '0';
                messageDiv.style.transition = 'opacity 0.3s ease';
                setTimeout(() => messageDiv.remove(), 300);
            }, 3000);
        }
    }
});

