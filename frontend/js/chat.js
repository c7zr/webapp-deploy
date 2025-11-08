const API_BASE = 'http://localhost:8000';
let ws = null;
let reconnectInterval = null;
let currentUser = null;

// Get token from localStorage
const token = localStorage.getItem('token');
if (!token) {
    window.location.href = '/login';
}

// Verify token and get user info
async function init() {
    try {
        const response = await fetch(`${API_BASE}/v2/user/profile`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (!response.ok) {
            localStorage.removeItem('token');
            window.location.href = '/login';
            return;
        }

        const data = await response.json();
        currentUser = data;
        
        // Connect to WebSocket
        connectWebSocket();
        
        // Load chat history
        loadChatHistory();
        
        // Load online users
        loadOnlineUsers();
        
    } catch (error) {
        console.error('Error initializing chat:', error);
        localStorage.removeItem('token');
        window.location.href = '/login';
    }
}

function connectWebSocket() {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.hostname}:8000/ws/chat?token=${token}`;
    
    ws = new WebSocket(wsUrl);
    
    ws.onopen = () => {
        console.log('Connected to chat');
        updateConnectionStatus(true);
        if (reconnectInterval) {
            clearInterval(reconnectInterval);
            reconnectInterval = null;
        }
    };
    
    ws.onclose = () => {
        console.log('Disconnected from chat');
        updateConnectionStatus(false);
        // Attempt to reconnect
        if (!reconnectInterval) {
            reconnectInterval = setInterval(() => {
                console.log('Attempting to reconnect...');
                connectWebSocket();
            }, 5000);
        }
    };
    
    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
    };
    
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleMessage(data);
    };
}

function handleMessage(data) {
    if (data.type === 'message') {
        addMessage(data);
    } else if (data.type === 'user_joined') {
        addSystemMessage(`${data.username} joined the chat`);
        loadOnlineUsers();
    } else if (data.type === 'user_left') {
        addSystemMessage(`${data.username} left the chat`);
        loadOnlineUsers();
    }
}

function addMessage(data) {
    const messagesContainer = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message';
    
    const avatar = data.username.charAt(0).toUpperCase();
    const time = new Date(data.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    
    messageDiv.innerHTML = `
        <div class="message-avatar">${avatar}</div>
        <div class="message-content">
            <div class="message-header">
                <span class="message-username">${escapeHtml(data.username)}</span>
                <span class="message-role ${data.role}">${data.role}</span>
                <span class="message-time">${time}</span>
            </div>
            <div class="message-text">${escapeHtml(data.message)}</div>
        </div>
    `;
    
    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function addSystemMessage(text) {
    const messagesContainer = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = 'system-message';
    messageDiv.textContent = text;
    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

async function loadChatHistory() {
    try {
        const response = await fetch(`${API_BASE}/v2/chat/history?limit=50`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (response.ok) {
            const data = await response.json();
            const messagesContainer = document.getElementById('chatMessages');
            messagesContainer.innerHTML = '';
            
            data.messages.forEach(msg => {
                addMessage(msg);
            });
        }
    } catch (error) {
        console.error('Error loading chat history:', error);
    }
}

async function loadOnlineUsers() {
    try {
        const response = await fetch(`${API_BASE}/v2/chat/users`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (response.ok) {
            const data = await response.json();
            const usersList = document.getElementById('usersList');
            const onlineCount = document.getElementById('onlineCount');
            
            onlineCount.textContent = data.count;
            
            usersList.innerHTML = data.users.map(user => `
                <div class="user-item">
                    <div class="user-status"></div>
                    <div class="user-info">
                        <div class="user-name">${escapeHtml(user.username)}</div>
                        <div class="user-role">${user.role}</div>
                    </div>
                </div>
            `).join('');
        }
    } catch (error) {
        console.error('Error loading online users:', error);
    }
}

function sendMessage() {
    const input = document.getElementById('messageInput');
    const message = input.value.trim();
    
    if (message && ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
            type: 'message',
            message: message
        }));
        
        input.value = '';
    }
}

function updateConnectionStatus(connected) {
    const statusDiv = document.getElementById('connectionStatus');
    if (connected) {
        statusDiv.textContent = 'Connected';
        statusDiv.classList.remove('disconnected');
    } else {
        statusDiv.textContent = 'Disconnected - Reconnecting...';
        statusDiv.classList.add('disconnected');
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Event Listeners
document.getElementById('sendBtn').addEventListener('click', sendMessage);

document.getElementById('messageInput').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        sendMessage();
    }
});

document.getElementById('logoutBtn').addEventListener('click', (e) => {
    e.preventDefault();
    if (ws) {
        ws.close();
    }
    localStorage.removeItem('token');
    window.location.href = '/login';
});

// Refresh online users every 10 seconds
setInterval(loadOnlineUsers, 10000);

// Initialize
init();
