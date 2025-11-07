// About Page Handler
document.addEventListener('DOMContentLoaded', async () => {
    await requireAuth();
    initProfileDropdown();
});

function checkAuth() {
    const token = localStorage.getItem('token') || sessionStorage.getItem('token');
    if (!token) {
        window.location.href = '/login';
        return;
    }
}

function logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    sessionStorage.removeItem('token');
    window.location.href = '/login';
}

