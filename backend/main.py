# SWATNFO Instagram Report Bot - Backend API (SQLite Version)
# Made by SWATNFO - d3sapiv2

from fastapi import FastAPI, HTTPException, Depends, status, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime, timedelta, timezone
from contextlib import asynccontextmanager
import jwt
import bcrypt
import requests
import sqlite3
import hashlib
import uuid
import os
import random
import time
import json

# Configuration
SECRET_KEY = os.environ.get("SECRET_KEY", "swatnfo_secret_key_change_in_production_2025_" + hashlib.sha256(str(datetime.now()).encode()).hexdigest()[:16])
DB_PATH = "swatnfo.db"
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")

# Security Configuration
security = HTTPBearer()
MAX_LOGIN_ATTEMPTS = 5
LOGIN_TIMEOUT = 900  # 15 minutes lockout after max attempts
PASSWORD_MIN_LENGTH = 8
TOKEN_EXPIRY_DAYS = 7

# Proxy Configuration
PROXY_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "proxies.txt")
proxies = []
proxy_index = 0  # For round-robin rotation
last_proxy_load_time = None

def load_proxies():
    """Load proxies from the proxy file"""
    global proxies, last_proxy_load_time
    try:
        # Try multiple possible locations
        possible_paths = [
            os.path.join(os.path.dirname(__file__), "..", "..", "proxies.txt"),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "proxies.txt"),
            "/home/ubuntu/webapp-deploy/proxies.txt",
            os.path.join(os.getcwd(), "proxies.txt"),
            "proxies.txt"
        ]
        
        loaded = False
        for path in possible_paths:
            try:
                abs_path = os.path.abspath(path)
                if os.path.exists(abs_path):
                    with open(abs_path, "r", encoding="utf-8") as f:
                        proxies = []
                        line_count = 0
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith("#"):
                                try:
                                    parts = line.split(":")
                                    if len(parts) == 4:
                                        host, port, username, password = parts
                                        proxies.append({
                                            "http": f"http://{username}:{password}@{host}:{port}",
                                            "https": f"http://{username}:{password}@{host}:{port}"
                                        })
                                        line_count += 1
                                except Exception as e:
                                    print(f"⚠️ Skipping invalid proxy line {line_count}: {str(e)}")
                                    continue
                    print(f"✅ Loaded {len(proxies)} proxies from {abs_path}")
                    last_proxy_load_time = datetime.now(timezone.utc)
                    loaded = True
                    break
            except Exception as e:
                continue
        
        if not loaded or len(proxies) == 0:
            print(f"❌ Failed to load proxies from any location")
            print(f"   Tried: {[os.path.abspath(p) for p in possible_paths]}")
        
        return len(proxies)
    except Exception as e:
        print(f"❌ Error loading proxies: {e}")
        return 0

def get_random_proxy(exclude_list=None):
    """Return a proxy using round-robin rotation"""
    global proxy_index
    
    # Reload proxies if not loaded or if we need a fresh list
    if not proxies or len(proxies) == 0:
        load_proxies()
    
    if not proxies or len(proxies) == 0:
        print("❌ No proxies available!")
        return None
    
    # Filter out excluded proxies
    if exclude_list:
        available_proxies = [p for p in proxies if p not in exclude_list]
    else:
        available_proxies = proxies
    
    if not available_proxies or len(available_proxies) == 0:
        print(f"⚠️ All proxies excluded! Total proxies: {len(proxies)}, Excluded: {len(exclude_list) if exclude_list else 0}")
        # If all proxies are excluded, reset and use all proxies
        available_proxies = proxies
    
    # Use round-robin for even distribution
    proxy_index = (proxy_index + 1) % len(available_proxies)
    selected = available_proxies[proxy_index]
    
    return selected

# Instagram User Agents Pool (for rotation to avoid detection)
INSTAGRAM_USER_AGENTS = [
    # Android Instagram App User Agents
    "Instagram 250.0.0.0.0 Android (30/11; 420dpi; 1080x2340; OnePlus; ONEPLUS A6000; OnePlus6; qcom; en_US; 232834545)",
    "Instagram 248.0.0.0.0 Android (29/10; 480dpi; 1080x2220; samsung; SM-G973F; beyond1; exynos9820; en_US; 229968015)",
    "Instagram 251.0.0.0.0 Android (31/12; 560dpi; 1440x3040; samsung; SM-G998B; p3s; exynos2100; en_US; 235678901)",
    "Instagram 249.0.0.0.0 Android (30/11; 440dpi; 1080x2400; Xiaomi; M2007J20CG; alioth; qcom; en_US; 231234567)",
    "Instagram 252.0.0.0.0 Android (32/12; 420dpi; 1080x2340; Google; Pixel 6; oriole; google; en_US; 237890123)",
    "Instagram 247.0.0.0.0 Android (28/9; 480dpi; 1080x2280; Huawei; VOG-L29; HWVOG; kirin980; en_US; 228901234)",
    "Instagram 253.0.0.0.0 Android (33/13; 560dpi; 1440x3200; OnePlus; LE2125; OnePlus9Pro; qcom; en_US; 240123456)",
    "Instagram 246.0.0.0.0 Android (29/10; 420dpi; 1080x2400; vivo; V2145; PD2145F; qcom; en_US; 227456789)",
    "Instagram 254.0.0.0.0 Android (31/12; 480dpi; 1080x2400; OPPO; CPH2247; OP4BA2; qcom; en_US; 242345678)",
    "Instagram 245.0.0.0.0 Android (30/11; 440dpi; 1080x2340; realme; RMX3085; RE54E4L1; qcom; en_US; 225567890)",
    "Instagram 255.0.0.0.0 Android (32/12; 560dpi; 1440x3120; samsung; SM-G991B; o1s; exynos2100; en_US; 243456789)",
    "Instagram 256.0.0.0.0 Android (33/13; 420dpi; 1080x2400; Xiaomi; 2201123G; lisa; qcom; en_US; 244567890)",
    "Instagram 257.0.0.0.0 Android (31/12; 480dpi; 1080x2340; OnePlus; DN2103; denniz; qcom; en_US; 245678901)",
    "Instagram 258.0.0.0.0 Android (32/12; 440dpi; 1080x2400; OPPO; CPH2473; OP4EC1; qcom; en_US; 246789012)",
    "Instagram 259.0.0.0.0 Android (33/13; 560dpi; 1440x3200; samsung; SM-S908B; b0s; exynos2200; en_US; 247890123)",
    "Instagram 260.0.0.0.0 Android (31/12; 420dpi; 1080x2340; Google; Pixel 7; panther; google; en_US; 248901234)",
    "Instagram 261.0.0.0.0 Android (32/12; 480dpi; 1080x2400; Xiaomi; 22081212UG; ruby; qcom; en_US; 249012345)",
    "Instagram 262.0.0.0.0 Android (33/13; 440dpi; 1080x2400; vivo; V2219; PD2219; qcom; en_US; 250123456)",
    "Instagram 263.0.0.0.0 Android (31/12; 560dpi; 1440x3120; OnePlus; CPH2449; OP535DL1; qcom; en_US; 251234567)",
    "Instagram 264.0.0.0.0 Android (32/12; 420dpi; 1080x2340; realme; RMX3516; RE58B2L1; qcom; en_US; 252345678)",
    # iOS Instagram App User Agents
    "Instagram 265.0.0.0.0 (iPhone14,2; iOS 16_0; en_US; en; scale=3.00; 1170x2532; 253456789)",
    "Instagram 266.0.0.0.0 (iPhone13,4; iOS 15_5; en_US; en; scale=3.00; 1284x2778; 254567890)",
    "Instagram 267.0.0.0.0 (iPhone14,5; iOS 16_1; en_US; en; scale=3.00; 1170x2532; 255678901)",
    "Instagram 268.0.0.0.0 (iPhone13,2; iOS 15_6; en_US; en; scale=3.00; 1170x2532; 256789012)",
    "Instagram 269.0.0.0.0 (iPhone14,3; iOS 16_2; en_US; en; scale=3.00; 1284x2778; 257890123)",
    "Instagram 270.0.0.0.0 (iPhone13,3; iOS 15_7; en_US; en; scale=3.00; 1284x2778; 258901234)",
    "Instagram 271.0.0.0.0 (iPhone14,4; iOS 16_3; en_US; en; scale=3.00; 1125x2436; 259012345)",
    "Instagram 272.0.0.0.0 (iPhone14,6; iOS 16_4; en_US; en; scale=3.00; 1170x2532; 260123456)",
    "Instagram 273.0.0.0.0 (iPhone13,1; iOS 15_8; en_US; en; scale=3.00; 1125x2436; 261234567)",
    "Instagram 274.0.0.0.0 (iPhone14,7; iOS 16_5; en_US; en; scale=3.00; 1284x2778; 262345678)"
]

# Web Browser User Agents for scraping
WEB_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
]

def get_random_user_agent():
    """Return a random Instagram user agent from the pool"""
    return random.choice(INSTAGRAM_USER_AGENTS)

def get_random_web_user_agent():
    """Return a random web browser user agent"""
    return random.choice(WEB_USER_AGENTS)

# Instagram API Configuration
INSTAGRAM_API_BASE = "https://www.instagram.com/api/v1"
INSTAGRAM_REPORT_METHODS = {
    "spam": {"reason_id": "1", "extra_data": ""},
    "self_injury": {"reason_id": "2", "extra_data": ""},
    "violent_threat": {"reason_id": "3", "extra_data": ""},
    "hate_speech": {"reason_id": "4", "extra_data": ""},
    "nudity": {"reason_id": "5", "extra_data": ""},
    "bullying": {"reason_id": "6", "extra_data": ""},
    "impersonation_me": {"reason_id": "1", "extra_data": ""},
    "tmnaofcl": {"reason_id": "1", "extra_data": "&action_type=celebrity&celebrity_username=tmnaofcl"},
    "sale_illegal": {"reason_id": "7", "extra_data": ""},
    "violence": {"reason_id": "8", "extra_data": ""},
    "intellectual_property": {"reason_id": "9", "extra_data": ""}
}

# Pydantic Models
class UserRegister(BaseModel):
    username: str
    email: Optional[str] = None
    password: str

class UserLogin(BaseModel):
    username: str
    password: str
    remember: bool = False

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None

class PasswordChange(BaseModel):
    currentPassword: str
    newPassword: str

class Credentials(BaseModel):
    sessionId: str
    csrfToken: str

class ReportRequest(BaseModel):
    target: str
    method: str

# Database Helper
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# Initialize Database
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Users table with security enhancements and approval system
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            isActive INTEGER DEFAULT 1,
            isProtected INTEGER DEFAULT 0,
            isApproved INTEGER DEFAULT 0,
            approvedBy TEXT,
            approvedAt TEXT,
            createdAt TEXT,
            reportCount INTEGER DEFAULT 0,
            failedLoginAttempts INTEGER DEFAULT 0,
            lastFailedLogin TEXT,
            accountLockedUntil TEXT
        )
    ''')
    
    # Credentials table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS credentials (
            userId TEXT PRIMARY KEY,
            sessionId TEXT,
            csrfToken TEXT,
            updatedAt TEXT
        )
    ''')
    
    # Reports table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reports (
            id TEXT PRIMARY KEY,
            userId TEXT,
            username TEXT,
            target TEXT,
            targetId TEXT,
            method TEXT,
            status TEXT,
            type TEXT,
            timestamp TEXT
        )
    ''')
    
    # Blacklist table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS blacklist (
            username TEXT PRIMARY KEY,
            reason TEXT NOT NULL,
            notes TEXT,
            added_by TEXT,
            blocked_attempts INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
    ''')
    
    # Settings table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT
        )
    ''')
    
    # Chat messages table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_messages (
            id TEXT PRIMARY KEY,
            userId TEXT NOT NULL,
            username TEXT NOT NULL,
            role TEXT NOT NULL,
            message TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    ''')
    
    # Initialize default settings
    cursor.execute("INSERT OR IGNORE INTO settings (key, value, updated_at) VALUES ('maintenanceMode', 'false', ?)", (datetime.now(timezone.utc).isoformat(),))
    cursor.execute("INSERT OR IGNORE INTO settings (key, value, updated_at) VALUES ('registrationEnabled', 'true', ?)", (datetime.now(timezone.utc).isoformat(),))
    cursor.execute("INSERT OR IGNORE INTO settings (key, value, updated_at) VALUES ('maxReportsPerUser', '5', ?)", (datetime.now(timezone.utc).isoformat(),))
    cursor.execute("INSERT OR IGNORE INTO settings (key, value, updated_at) VALUES ('maxBulkTargets', '200', ?)", (datetime.now(timezone.utc).isoformat(),))
    cursor.execute("INSERT OR IGNORE INTO settings (key, value, updated_at) VALUES ('maxPremiumBulkTargets', '500', ?)", (datetime.now(timezone.utc).isoformat(),))
    cursor.execute("INSERT OR IGNORE INTO settings (key, value, updated_at) VALUES ('dailyReportLimit', '5', ?)", (datetime.now(timezone.utc).isoformat(),))
    cursor.execute("INSERT OR IGNORE INTO settings (key, value, updated_at) VALUES ('apiTimeout', '30', ?)", (datetime.now(timezone.utc).isoformat(),))
    cursor.execute("INSERT OR IGNORE INTO settings (key, value, updated_at) VALUES ('rateLimitPerMinute', '60', ?)", (datetime.now(timezone.utc).isoformat(),))
    cursor.execute("INSERT OR IGNORE INTO settings (key, value, updated_at) VALUES ('requireApproval', 'false', ?)", (datetime.now(timezone.utc).isoformat(),))
    
    conn.commit()
    
    # Create owner account
    cursor.execute("SELECT * FROM users WHERE username = ?", ("sw4t",))
    if not cursor.fetchone():
        owner_id = "owner_" + hashlib.md5(b"sw4t").hexdigest()
        hashed_pw = bcrypt.hashpw("SwAtNf0!2024#Pr0T3cT3d".encode(), bcrypt.gensalt()).decode()
        cursor.execute('''
            INSERT INTO users (id, username, email, password, role, isActive, isProtected, isApproved, approvedBy, approvedAt, createdAt, reportCount)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (owner_id, "sw4t", "owner@swatnfo.com", hashed_pw, "owner", 1, 1, 1, "system", datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat(), 0))
        conn.commit()
        print("✅ Owner account created: sw4t")
    
    conn.close()

# Lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    print("=" * 50)
    print("✅ SWATNFO Backend Started!")
    print("✅ Database: SQLite (no MongoDB needed)")
    print("✅ API: http://localhost:8000")
    print("✅ Docs: http://localhost:8000/docs")
    print("=" * 50)
    print("Default Login: sw4t / SwAtNf0!2024#Pr0T3cT3d")
    print("=" * 50)
    yield

# FastAPI App
app = FastAPI(title="SWATNFO API v2", version="2.0.0", lifespan=lifespan)

# Mount static files (CSS, JS)
app.mount("/css", StaticFiles(directory=os.path.join(FRONTEND_DIR, "css")), name="css")
app.mount("/js", StaticFiles(directory=os.path.join(FRONTEND_DIR, "js")), name="js")
app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIR, "assets")), name="assets")

# CORS - Allow all origins in development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins in development
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"]  # Allow all headers
)

# WebSocket Connection Manager for Chat
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[dict] = []

    async def connect(self, websocket: WebSocket, user_info: dict):
        await websocket.accept()
        self.active_connections.append({"websocket": websocket, "user": user_info})
        print(f"✅ User {user_info['username']} connected to chat")

    def disconnect(self, websocket: WebSocket):
        for conn in self.active_connections:
            if conn["websocket"] == websocket:
                self.active_connections.remove(conn)
                print(f"❌ User {conn['user']['username']} disconnected from chat")
                break

    async def broadcast(self, message: dict):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection["websocket"].send_json(message)
            except:
                disconnected.append(connection)
        
        # Remove disconnected clients
        for conn in disconnected:
            self.disconnect(conn["websocket"])

manager = ConnectionManager()

# Rate limiting storage (in-memory, use Redis in production)
rate_limit_storage = {}

def check_rate_limit(identifier: str, max_requests: int = 10, window_seconds: int = 60) -> bool:
    """Simple rate limiter - blocks excessive requests"""
    now = datetime.now(timezone.utc)
    
    if identifier not in rate_limit_storage:
        rate_limit_storage[identifier] = []
    
    # Clean old requests outside the time window
    rate_limit_storage[identifier] = [
        req_time for req_time in rate_limit_storage[identifier]
        if (now - req_time).total_seconds() < window_seconds
    ]
    
    # Check if limit exceeded
    if len(rate_limit_storage[identifier]) >= max_requests:
        return False
    
    # Add current request
    rate_limit_storage[identifier].append(now)
    return True

# Helper Functions
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

def create_token(user_id: str, username: str, role: str, remember: bool = False) -> str:
    expiry = timedelta(days=TOKEN_EXPIRY_DAYS) if remember else timedelta(hours=12)
    payload = {
        "user_id": user_id,
        "username": username,
        "role": role,
        "exp": datetime.now(timezone.utc) + expiry,
        "iat": datetime.now(timezone.utc),
        "jti": str(uuid.uuid4())  # Unique token ID
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (payload["user_id"],))
        user = cursor.fetchone()
        conn.close()
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def verify_admin(token_data: dict = Depends(verify_token)):
    if token_data["role"] not in ["admin", "owner"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    return token_data

# Routes
# Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    # XSS Protection
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    # Don't add HSTS in development (only HTTPS)
    # response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    
    # Prevent browser caching for JavaScript and CSS files
    if request.url.path.endswith(('.js', '.css', '.html')):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    
    return response

@app.get("/", response_class=HTMLResponse)
async def root():
    """Redirect to login page"""
    return RedirectResponse(url="/login")

@app.get("/login", response_class=HTMLResponse)
async def login_page():
    """Serve login page"""
    return FileResponse(os.path.join(FRONTEND_DIR, "login.html"))

@app.get("/register", response_class=HTMLResponse)
async def register_page():
    """Serve register page"""
    return FileResponse(os.path.join(FRONTEND_DIR, "register.html"))

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page():
    """Serve dashboard page"""
    return FileResponse(os.path.join(FRONTEND_DIR, "dashboard.html"))

@app.get("/reporting", response_class=HTMLResponse)
async def reporting_page():
    """Serve reporting page"""
    return FileResponse(os.path.join(FRONTEND_DIR, "reporting.html"))

@app.get("/history", response_class=HTMLResponse)
async def history_page():
    """Serve history page"""
    return FileResponse(os.path.join(FRONTEND_DIR, "history.html"))

@app.get("/settings", response_class=HTMLResponse)
async def settings_page():
    """Serve settings page"""
    return FileResponse(os.path.join(FRONTEND_DIR, "settings.html"))

@app.get("/about", response_class=HTMLResponse)
async def about_page():
    """Serve about page"""
    return FileResponse(os.path.join(FRONTEND_DIR, "about.html"))

@app.get("/admin", response_class=HTMLResponse)
async def admin_page():
    """Serve admin page"""
    return FileResponse(os.path.join(FRONTEND_DIR, "admin.html"))

@app.get("/api")
async def api_info():
    return {
        "name": "Instagram Report Bot API",
        "version": "2.0.0",
        "status": "online"
    }

# Auth Routes
@app.post("/v2/auth/register")
async def register(user: UserRegister):
    conn = None
    try:
        # Rate limiting for registration
        rate_limit_key = f"register_{user.email if user.email else user.username}"
        if not check_rate_limit(rate_limit_key, max_requests=3, window_seconds=300):
            return JSONResponse(
                status_code=429,
                content={"message": "Too many registration attempts. Please try again later.", "error": True}
            )
        
        # Validate password strength
        if len(user.password) < PASSWORD_MIN_LENGTH:
            return JSONResponse(
                status_code=400,
                content={"message": f"Password must be at least {PASSWORD_MIN_LENGTH} characters long", "error": True}
            )
        
        # Check for password complexity
        if not any(c.isupper() for c in user.password):
            return JSONResponse(
                status_code=400,
                content={"message": "Password must contain at least one uppercase letter", "error": True}
            )
        if not any(c.islower() for c in user.password):
            return JSONResponse(
                status_code=400,
                content={"message": "Password must contain at least one lowercase letter", "error": True}
            )
        if not any(c.isdigit() for c in user.password):
            return JSONResponse(
                status_code=400,
                content={"message": "Password must contain at least one number", "error": True}
            )
        
        # Validate username (alphanumeric and underscores only)
        if not user.username.replace('_', '').isalnum():
            return JSONResponse(
                status_code=400,
                content={"message": "Username can only contain letters, numbers, and underscores", "error": True}
            )
        
        if len(user.username) < 1 or len(user.username) > 20:
            return JSONResponse(
                status_code=400,
                content={"message": "Username must be between 1 and 20 characters", "error": True}
            )
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Check if username exists
        cursor.execute("SELECT * FROM users WHERE username = ?", (user.username,))
        if cursor.fetchone():
            conn.close()
            return JSONResponse(
                status_code=400,
                content={"message": "Username already exists", "error": True}
            )
        
        # Check if email exists (only if provided)
        if user.email:
            cursor.execute("SELECT * FROM users WHERE email = ?", (user.email,))
            if cursor.fetchone():
                conn.close()
                return JSONResponse(
                    status_code=400,
                    content={"message": "Email already exists", "error": True}
                )
        
        # Use provided email or generate placeholder
        email = user.email if user.email else f"{user.username}@local.user"
        
        user_id = "user_" + str(uuid.uuid4())[:8]
        hashed_pw = hash_password(user.password)
        
        # Approval system removed - all users are auto-approved
        is_approved = 1
        approved_by = "auto"
        approved_at = datetime.now(timezone.utc).isoformat()
        
        cursor.execute('''
            INSERT INTO users (id, username, email, password, role, isActive, isProtected, isApproved, approvedBy, approvedAt, createdAt, reportCount, failedLoginAttempts, lastFailedLogin, accountLockedUntil)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, user.username, email, hashed_pw, "user", 1, 0, is_approved, approved_by, approved_at, datetime.now(timezone.utc).isoformat(), 0, 0, None, None))
        
        conn.commit()
        conn.close()
        
        return JSONResponse(
            status_code=200,
            content={
                "message": "Account created successfully",
                "success": True,
                "requiresApproval": False
            }
        )
            
    except Exception as e:
        print(f"⚠️ Registration error: {str(e)}")
        if conn:
            conn.close()
        return JSONResponse(
            status_code=500,
            content={
                "message": "Internal server error during registration",
                "error": True
            }
        )

@app.post("/v2/auth/login")
async def login(credentials: UserLogin):
    # Rate limiting for login attempts
    if not check_rate_limit(f"login_{credentials.username}", max_requests=5, window_seconds=300):
        raise HTTPException(status_code=429, detail="Too many login attempts. Please try again in 5 minutes.")
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Check if username exists (use parameterized queries to prevent SQL injection)
    cursor.execute("SELECT * FROM users WHERE username = ?", (credentials.username,))
    user = cursor.fetchone()
    
    if not user:
        conn.close()
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Check if account is locked
    if user["accountLockedUntil"]:
        locked_until = datetime.fromisoformat(user["accountLockedUntil"])
        if datetime.now(timezone.utc) < locked_until:
            conn.close()
            raise HTTPException(status_code=403, detail=f"Account locked due to too many failed login attempts. Try again later.")
        else:
            # Unlock account if time has passed
            cursor.execute("UPDATE users SET failedLoginAttempts = 0, accountLockedUntil = NULL WHERE id = ?", (user["id"],))
            conn.commit()
    
    # Verify password
    if not verify_password(credentials.password, user["password"]):
        # Increment failed login attempts
        failed_attempts = user["failedLoginAttempts"] + 1
        
        if failed_attempts >= MAX_LOGIN_ATTEMPTS:
            # Lock account
            locked_until = datetime.now(timezone.utc) + timedelta(seconds=LOGIN_TIMEOUT)
            cursor.execute(
                "UPDATE users SET failedLoginAttempts = ?, lastFailedLogin = ?, accountLockedUntil = ? WHERE id = ?",
                (failed_attempts, datetime.now(timezone.utc).isoformat(), locked_until.isoformat(), user["id"])
            )
            conn.commit()
            conn.close()
            raise HTTPException(status_code=403, detail=f"Account locked due to too many failed login attempts. Try again in {LOGIN_TIMEOUT//60} minutes.")
        else:
            # Update failed attempts
            cursor.execute(
                "UPDATE users SET failedLoginAttempts = ?, lastFailedLogin = ? WHERE id = ?",
                (failed_attempts, datetime.now(timezone.utc).isoformat(), user["id"])
            )
            conn.commit()
            conn.close()
            raise HTTPException(status_code=401, detail=f"Invalid credentials. {MAX_LOGIN_ATTEMPTS - failed_attempts} attempts remaining.")
    
    # Check if account is active
    if not user["isActive"]:
        conn.close()
        raise HTTPException(status_code=403, detail="Account is disabled")
    
    # Approval system removed - all users are auto-approved
    
    # Reset failed login attempts on successful login
    cursor.execute("UPDATE users SET failedLoginAttempts = 0, lastFailedLogin = NULL, accountLockedUntil = NULL WHERE id = ?", (user["id"],))
    conn.commit()
    conn.close()
    
    # Create token with remember option
    token = create_token(user["id"], user["username"], user["role"], credentials.remember)
    
    return {
        "token": token,
        "user": {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "role": user["role"]
        }
    }

# User Routes
@app.get("/v2/user/profile")
async def get_profile(token_data: dict = Depends(verify_token)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (token_data["user_id"],))
    user = cursor.fetchone()
    conn.close()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "username": user["username"],
        "email": user["email"],
        "role": user["role"],
        "reportCount": user["reportCount"],
        "createdAt": user["createdAt"]
    }

@app.put("/v2/user/update")
async def update_user(update: UserUpdate, token_data: dict = Depends(verify_token)):
    if update.email:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET email = ? WHERE id = ?", (update.email, token_data["user_id"]))
        conn.commit()
        
        cursor.execute("SELECT * FROM users WHERE id = ?", (token_data["user_id"],))
        user = cursor.fetchone()
        conn.close()
        
        return {"message": "Profile updated", "user": {
            "username": user["username"],
            "email": user["email"]
        }}
    return {"message": "Nothing to update"}

@app.put("/v2/user/password")
async def change_password(change: PasswordChange, token_data: dict = Depends(verify_token)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (token_data["user_id"],))
    user = cursor.fetchone()
    
    if not verify_password(change.currentPassword, user["password"]):
        conn.close()
        raise HTTPException(status_code=401, detail="Current password is incorrect")
    
    new_hash = hash_password(change.newPassword)
    cursor.execute("UPDATE users SET password = ? WHERE id = ?", (new_hash, token_data["user_id"]))
    conn.commit()
    conn.close()
    
    return {"message": "Password changed successfully"}

@app.delete("/v2/user/delete")
async def delete_user(token_data: dict = Depends(verify_token)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (token_data["user_id"],))
    user = cursor.fetchone()
    
    if user["isProtected"]:
        conn.close()
        raise HTTPException(status_code=403, detail="Protected account cannot be deleted")
    
    cursor.execute("DELETE FROM users WHERE id = ?", (token_data["user_id"],))
    cursor.execute("DELETE FROM credentials WHERE userId = ?", (token_data["user_id"],))
    cursor.execute("DELETE FROM reports WHERE userId = ?", (token_data["user_id"],))
    conn.commit()
    conn.close()
    
    return {"message": "Account deleted successfully"}

# Credentials Routes
@app.get("/v2/credentials")
async def get_credentials(token_data: dict = Depends(verify_token)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM credentials WHERE userId = ?", (token_data["user_id"],))
    cred = cursor.fetchone()
    conn.close()
    
    if not cred:
        return {"credentials": None, "configured": False}
    
    return {
        "credentials": {
            "sessionId": cred["sessionId"],
            "csrfToken": cred["csrfToken"],
            "isValid": True
        },
        "configured": True
    }

@app.post("/v2/credentials")
async def save_credentials(creds: Credentials, token_data: dict = Depends(verify_token)):
    print(f"🔐 Credential save attempt for user {token_data['user_id']}")
    print(f"   SessionId: {creds.sessionId[:20]}... (truncated)")
    print(f"   CsrfToken: {creds.csrfToken[:20]}... (truncated)")
    
    conn = get_db()
    cursor = conn.cursor()
    
    # First, test if the credentials are valid
    try:
        print(f"🧪 Testing credentials with Instagram API...")
        test_headers = {
            "User-Agent": get_random_user_agent(),
            "Cookie": f"sessionid={creds.sessionId}; csrftoken={creds.csrfToken}",
            "X-CSRFToken": creds.csrfToken
        }
        
        # Test with a simple profile info request
        test_response = requests.get(
            "https://www.instagram.com/api/v1/web/accounts/web_create_ajax/attempt/",
            headers=test_headers,
            timeout=10
        )
        
        print(f"   Test Response Status: {test_response.status_code}")
        
        # If we get 403 or 200, credentials are being accepted (logged in)
        # If we get 401, credentials are invalid
        if test_response.status_code == 401:
            conn.close()
            print(f"❌ Credentials rejected by Instagram (401)")
            raise HTTPException(status_code=400, detail="Invalid Instagram credentials - please log in again and get fresh sessionid/csrftoken")
        
        print(f"✅ Credentials validated successfully")
            
    except requests.exceptions.RequestException as e:
        # Network error, but save anyway
        print(f"⚠️ Network error during validation: {e}")
        pass
    
    cursor.execute("SELECT * FROM credentials WHERE userId = ?", (token_data["user_id"],))
    existing = cursor.fetchone()
    
    if existing:
        print(f"📝 Updating existing credentials for user {token_data['user_id']}")
        cursor.execute('''
            UPDATE credentials SET sessionId = ?, csrfToken = ?, updatedAt = ?
            WHERE userId = ?
        ''', (creds.sessionId, creds.csrfToken, datetime.now(timezone.utc).isoformat(), token_data["user_id"]))
    else:
        print(f"📝 Inserting new credentials for user {token_data['user_id']}")
        cursor.execute('''
            INSERT INTO credentials (userId, sessionId, csrfToken, updatedAt)
            VALUES (?, ?, ?, ?)
        ''', (token_data["user_id"], creds.sessionId, creds.csrfToken, datetime.now(timezone.utc).isoformat()))
    
    conn.commit()
    print(f"💾 Credentials saved to database successfully")
    conn.close()
    
    return {"message": "Credentials saved and verified successfully", "success": True}

@app.post("/v2/credentials/test")
async def test_credentials(token_data: dict = Depends(verify_token)):
    print(f"🧪 Testing credentials for user {token_data['user_id']}")
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM credentials WHERE userId = ?", (token_data["user_id"],))
    cred = cursor.fetchone()
    conn.close()
    
    if not cred:
        print(f"❌ No credentials found for user {token_data['user_id']}")
        return {"valid": False, "message": "No credentials configured"}
    
    print(f"   SessionId: {cred['sessionId'][:20]}... (truncated)")
    
    try:
        # Use random user agent for credentials test
        headers = {
            "User-Agent": get_random_user_agent(),
            "Cookie": f"sessionid={cred['sessionId']}"
        }
        
        print(f"   Sending test request to Instagram...")
        response = requests.get(
            "https://www.instagram.com/api/v1/accounts/current_user/",
            headers=headers,
            timeout=10
        )
        
        print(f"   Response Status: {response.status_code}")
        
        if response.status_code == 200:
            print(f"✅ Credentials are valid!")
            return {"valid": True, "message": "Credentials are valid"}
        else:
            print(f"❌ Credentials invalid (status {response.status_code})")
            return {"valid": False, "message": f"Invalid credentials (status {response.status_code})"}
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return {"valid": False, "message": "Connection error"}

# Reporting Routes
@app.post("/v2/reports/send")
async def send_report(report: ReportRequest, token_data: dict = Depends(verify_token), is_bulk: bool = False):
    conn = get_db()
    cursor = conn.cursor()
    
    # Get user info to check role
    cursor.execute("SELECT role FROM users WHERE id = ?", (token_data["user_id"],))
    user = cursor.fetchone()
    user_role = user["role"] if user else "user"
    
    # Check if bulk reporting is allowed
    if is_bulk and user_role not in ["premium", "admin", "owner"]:
        conn.close()
        raise HTTPException(
            status_code=403, 
            detail="Bulk reporting is exclusive to Premium users. Contact SWATNFO or Xefi for payment to upgrade your account."
        )
    
    # Check daily report limit for regular users (100 reports per day)
    if user_role == "user":
        # Get today's date at midnight
        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        cursor.execute(
            "SELECT COUNT(*) as count FROM reports WHERE userId = ? AND timestamp >= ?",
            (token_data["user_id"], today)
        )
        daily_count = cursor.fetchone()["count"]
        
        if daily_count >= 100:
            conn.close()
            raise HTTPException(
                status_code=429,
                detail="Daily report limit reached (100/day). Upgrade to Premium for unlimited reports. Contact SWATNFO or Xefi for payment."
            )
    
    # Check if target is blacklisted
    cursor.execute("SELECT * FROM blacklist WHERE username = ?", (report.target.lower(),))
    blacklisted = cursor.fetchone()
    
    if blacklisted:
        # Increment blocked attempts
        cursor.execute("UPDATE blacklist SET blocked_attempts = blocked_attempts + 1 WHERE username = ?", (report.target.lower(),))
        conn.commit()
        conn.close()
        raise HTTPException(status_code=403, detail=f"Target @{report.target} is blacklisted and cannot be reported")
    
    cursor.execute("SELECT * FROM credentials WHERE userId = ?", (token_data["user_id"],))
    cred = cursor.fetchone()
    
    if not cred:
        conn.close()
        print(f"❌ No credentials found for user {token_data['user_id']}")
        raise HTTPException(status_code=400, detail="Please configure Instagram credentials first")
    
    print(f"✅ Credentials loaded for user {token_data['user_id']}")
    print(f"📝 Attempting to report @{report.target} using method: {report.method}")
    
    # Get report method details
    if report.method not in INSTAGRAM_REPORT_METHODS:
        conn.close()
        raise HTTPException(status_code=400, detail="Invalid report method")
    
    method_details = INSTAGRAM_REPORT_METHODS[report.method]
    
    # Check if user has reported this target in the last 3 minutes (for single reports only)
    # Only apply cooldown to regular users, not premium/admin/owner
    if not is_bulk and user_role == "user":
        three_minutes_ago = (datetime.now(timezone.utc) - timedelta(minutes=3)).isoformat()
        cursor.execute(
            "SELECT timestamp FROM reports WHERE userId = ? AND target = ? AND timestamp >= ? ORDER BY timestamp DESC LIMIT 1",
            (token_data["user_id"], report.target, three_minutes_ago)
        )
        recent_report = cursor.fetchone()
        
        if recent_report:
            # Calculate time remaining
            last_report_time = datetime.fromisoformat(recent_report["timestamp"])
            time_diff = datetime.now(timezone.utc) - last_report_time
            seconds_remaining = 180 - int(time_diff.total_seconds())
            minutes_remaining = seconds_remaining // 60
            secs_remaining = seconds_remaining % 60
            
            conn.close()
            raise HTTPException(
                status_code=400, 
                detail=f"Please wait {minutes_remaining}m {secs_remaining}s before reporting @{report.target} again. Upgrade to Premium for unlimited bulk reporting."
            )

    # Get target user ID from Instagram using EXACT logic from swatnfobest.py
    target_id = None
    success = False
    error_msg = None
    
    try:
        # Method 1: API lookup (EXACT from swatnfobest.py)
        print(f"🔍 Method 1: API lookup for @{report.target}")
        try:
            r2 = requests.post(
                'https://i.instagram.com:443/api/v1/users/lookup/',
                headers={
                    "Connection": "close",
                    "X-IG-Connection-Type": "WIFI",
                    "mid": "XOSINgABAAG1IDmaral3noOozrK0rrNSbPuSbzHq",
                    "X-IG-Capabilities": "3R4=",
                    "Accept-Language": "en-US",
                    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                    "User-Agent": "Instagram 99.4.0",
                    "Accept-Encoding": "gzip, deflate"
                },
                data={
                    "signed_body": f'35a2d547d3b6ff400f713948cdffe0b789a903f86117eb6e2f3e573079b2f038.{{"q":"{report.target}"}}'
                },
                timeout=30
            )
            
            print(f"   Status: {r2.status_code}")
            if 'No users found' not in r2.text and '"spam":true' not in r2.text:
                try:
                    target_id = str(r2.json()['user_id'])
                    print(f"   ✅ Found target ID via API: {target_id}")
                except KeyError:
                    print(f"   ❌ KeyError in API response")
        except Exception as e:
            print(f"   ❌ Method 1 failed: {str(e)[:100]}")
        
        # Method 2: Web scraping (EXACT from swatnfobest.py)
        if not target_id:
            print(f"🔍 Method 2: Web scraping for @{report.target}")
            try:
                import re
                adv_search = requests.get(
                    f'https://www.instagram.com/{report.target}',
                    headers={
                        'Host': 'www.instagram.com',
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/110.0',
                        'Cookie': f'csrftoken={cred["csrfToken"]}',
                    },
                    timeout=30
                )
                
                print(f"   Status: {adv_search.status_code}")
                patterns = [
                    r'"profile_id":"(.*?)"',
                    r'"page_id":"profilePage_(.*?)"'
                ]
                
                for pattern in patterns:
                    match = re.findall(pattern, adv_search.text)
                    if match:
                        target_id = match[0]
                        print(f"   ✅ Found target ID via scraping: {target_id}")
                        break
            except Exception as e:
                print(f"   ❌ Method 2 failed: {str(e)[:100]}")
        
        # Method 3: Web API (EXACT from swatnfobest.py)
        if not target_id:
            print(f"🔍 Method 3: Web API for @{report.target}")
            try:
                adv_search2 = requests.get(
                    f'https://www.instagram.com/api/v1/users/web_profile_info/?username={report.target}',
                    headers={
                        'Host': 'www.instagram.com',
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/110.0',
                        'X-CSRFToken': cred["csrfToken"],
                        'X-IG-App-ID': '936619743392459',
                        'Cookie': f'sessionid={cred["sessionId"]}'
                    },
                    timeout=30
                )
                
                print(f"   Status: {adv_search2.status_code}")
                target_id = str(adv_search2.json()['data']['user']['id'])
                print(f"   ✅ Found target ID via web API: {target_id}")
            except Exception as e:
                print(f"   ❌ Method 3 failed: {str(e)[:100]}")
        
        if not target_id:
            success = False
            error_msg = "Target user not found - please check the username"
            print(f"❌ All methods failed to find @{report.target}")
        else:
            # Send report using EXACT logic from swatnfobest.py
            print(f"📤 Sending report to Instagram")
            print(f"   Target ID: {target_id}")
            print(f"   Reason ID: {method_details['reason_id']}")
            
            # Use EXACT headers from swatnfobest.py
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/110.0",
                "Host": "i.instagram.com",
                'cookie': f"sessionid={cred['sessionId']}",
                "X-CSRFToken": cred["csrfToken"],
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
            }
            
            # Build data EXACTLY as swatnfobest.py does
            extra_data = method_details.get("extra_data", "")
            data = f'source_name=&reason_id={method_details["reason_id"]}&frx_context={extra_data}'
            
            try:
                r3 = requests.post(
                    f"https://i.instagram.com/users/{target_id}/flag/",
                    headers=headers,
                    data=data,
                    allow_redirects=False,
                    timeout=30
                )
                
                print(f"   📨 Response Status: {r3.status_code}")
                
                # Handle response EXACTLY as swatnfobest.py does
                if r3.status_code == 429:
                    success = False
                    error_msg = "Rate limited! Please wait before sending more reports."
                    print(f"❌ Rate limited")
                elif r3.status_code == 500:
                    success = False
                    error_msg = "Target not found!"
                    print(f"❌ Target not found (500)")
                elif r3.status_code in [200, 302]:
                    success = True
                    error_msg = None
                    print(f"✅ Report successful!")
                else:
                    # Sometimes reports work even with unexpected status codes
                    success = True
                    error_msg = None
                    print(f"✅ Unexpected status {r3.status_code}, marking as success")
                    
            except requests.exceptions.TooManyRedirects:
                # From swatnfobest.py - this means success
                success = True
                error_msg = None
                print(f"✅ Report successful (redirect)")
            except Exception as e:
                success = False
                error_msg = f"Error sending report: {str(e)}"
                print(f"❌ Exception during report: {e}")
                
    except Exception as e:
        success = False
        error_msg = str(e)
        print(f"❌ Exception during report: {e}")
        import traceback
        traceback.print_exc()
    
    # Log report
    report_id = str(uuid.uuid4())
    cursor.execute('''
        INSERT INTO reports (id, userId, username, target, targetId, method, status, type, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (report_id, token_data["user_id"], token_data["username"], report.target, 
          target_id if target_id else "unknown", report.method, 
          "success" if success else "failed", "single", 
          datetime.now(timezone.utc).isoformat()))
    
    if success:
        cursor.execute("UPDATE users SET reportCount = reportCount + 1 WHERE id = ?", (token_data["user_id"],))
    
    conn.commit()
    conn.close()
    
    if success:
        return {"success": True, "message": "Report sent successfully"}
    else:
        return {"success": False, "message": error_msg or "Report failed"}

@app.get("/v2/reports/stats")
async def get_stats(token_data: dict = Depends(verify_token)):
    conn = get_db()
    cursor = conn.cursor()
    
    # Get user role
    cursor.execute("SELECT role FROM users WHERE id = ?", (token_data["user_id"],))
    user = cursor.fetchone()
    user_role = user["role"] if user else "user"
    
    cursor.execute("SELECT COUNT(*) as total FROM reports WHERE userId = ?", (token_data["user_id"],))
    total = cursor.fetchone()["total"]
    
    cursor.execute("SELECT COUNT(*) as success FROM reports WHERE userId = ? AND status = 'success'", (token_data["user_id"],))
    successful = cursor.fetchone()["success"]
    
    cursor.execute("SELECT COUNT(*) as failed FROM reports WHERE userId = ? AND status = 'failed'", (token_data["user_id"],))
    failed = cursor.fetchone()["failed"]
    
    cursor.execute("SELECT COUNT(DISTINCT target) as targets FROM reports WHERE userId = ?", (token_data["user_id"],))
    targets = cursor.fetchone()["targets"]
    
    # Get today's report count for daily limit
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    cursor.execute(
        "SELECT COUNT(*) as count FROM reports WHERE userId = ? AND timestamp >= ?",
        (token_data["user_id"], today)
    )
    daily_count = cursor.fetchone()["count"]
    
    # Get daily limit from settings
    cursor.execute("SELECT value FROM settings WHERE key = 'dailyReportLimit'")
    daily_limit_row = cursor.fetchone()
    daily_limit = int(daily_limit_row["value"]) if daily_limit_row else 100
    
    conn.close()
    
    return {
        "total": total,
        "successful": successful,
        "failed": failed,
        "targets": targets,
        "dailyCount": daily_count,
        "dailyLimit": daily_limit if user_role == "user" else None,
        "canBulkReport": user_role in ["premium", "admin", "owner"],
        "role": user_role
    }

@app.get("/v2/reports/recent")
async def get_recent_reports(limit: int = 10, token_data: dict = Depends(verify_token)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM reports WHERE userId = ? ORDER BY timestamp DESC LIMIT ?
    ''', (token_data["user_id"], limit))
    reports = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return {"reports": reports}

@app.get("/v2/reports/history")
async def get_history(
    page: int = 1,
    limit: int = 50,
    status: str = "all",
    method: str = "all",
    search: str = "",
    token_data: dict = Depends(verify_token)
):
    conn = get_db()
    cursor = conn.cursor()
    
    query = "SELECT * FROM reports WHERE userId = ?"
    params = [token_data["user_id"]]
    
    if status != "all":
        query += " AND status = ?"
        params.append(status)
    if method != "all":
        query += " AND method = ?"
        params.append(method)
    if search:
        query += " AND target LIKE ?"
        params.append(f"%{search}%")
    
    query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
    params.extend([limit, (page - 1) * limit])
    
    cursor.execute(query, params)
    reports = [dict(row) for row in cursor.fetchall()]
    
    # Get stats
    cursor.execute("SELECT COUNT(*) as total FROM reports WHERE userId = ?", (token_data["user_id"],))
    total_reports = cursor.fetchone()["total"]
    
    cursor.execute("SELECT COUNT(*) as success FROM reports WHERE userId = ? AND status = 'success'", (token_data["user_id"],))
    success_count = cursor.fetchone()["success"]
    
    cursor.execute("SELECT COUNT(*) as failed FROM reports WHERE userId = ? AND status = 'failed'", (token_data["user_id"],))
    failed_count = cursor.fetchone()["failed"]
    
    conn.close()
    
    return {
        "reports": reports,
        "stats": {
            "total": total_reports,
            "successful": success_count,
            "failed": failed_count
        },
        "pagination": {
            "currentPage": page,
            "totalPages": (len(reports) + limit - 1) // limit if reports else 1,
            "total": len(reports)
        }
    }

@app.delete("/v2/reports/clear")
async def clear_history(token_data: dict = Depends(verify_token)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM reports WHERE userId = ?", (token_data["user_id"],))
    conn.commit()
    conn.close()
    return {"message": "History cleared successfully"}

# Admin Routes
@app.get("/v2/admin/stats")
async def admin_stats(token_data: dict = Depends(verify_admin)):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) as total FROM users")
    total_users = cursor.fetchone()["total"]
    
    cursor.execute("SELECT COUNT(*) as total FROM reports")
    total_reports = cursor.fetchone()["total"]
    
    cursor.execute("SELECT COUNT(*) as success FROM reports WHERE status = 'success'")
    successful = cursor.fetchone()["success"]
    
    success_rate = (successful / total_reports * 100) if total_reports > 0 else 0
    
    conn.close()
    
    return {
        "totalUsers": total_users,
        "totalReports": total_reports,
        "successRate": round(success_rate, 1),
        "activeToday": 0
    }

@app.get("/v2/admin/users")
async def admin_get_users(token_data: dict = Depends(verify_admin)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    users = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return {"users": users}

@app.get("/v2/admin/users/{user_id}")
async def admin_get_user(user_id: str, token_data: dict = Depends(verify_admin)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return dict(user)

@app.post("/v2/admin/users")
async def admin_create_user(user_data: dict, token_data: dict = Depends(verify_admin)):
    """Admin endpoint to create new user"""
    conn = get_db()
    cursor = conn.cursor()
    try:
        username = user_data.get("username", "").strip()
        email = user_data.get("email", "").strip()
        password = user_data.get("password", "")
        role = user_data.get("role", "user")

        if not username or not email or not password:
            conn.close()
            return JSONResponse(status_code=400, content={"message": "Username, email, and password are required", "error": True})

        if len(password) < PASSWORD_MIN_LENGTH:
            conn.close()
            return JSONResponse(status_code=400, content={"message": f"Password must be at least {PASSWORD_MIN_LENGTH} characters", "error": True})

        # Check if username exists
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            conn.close()
            return JSONResponse(status_code=400, content={"message": "Username already exists", "error": True})

        # Check if email exists
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        if cursor.fetchone():
            conn.close()
            return JSONResponse(status_code=400, content={"message": "Email already exists", "error": True})

        # Hash password
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        user_id = str(uuid.uuid4())

        # Admin-created users are auto-approved
        cursor.execute('''
            INSERT INTO users (id, username, email, password, role, isActive, isProtected, isApproved, approvedBy, approvedAt, createdAt, reportCount, failedLoginAttempts)
            VALUES (?, ?, ?, ?, ?, 1, 0, 1, ?, ?, ?, 0, 0)
        ''', (user_id, username, email, hashed_password, role, token_data["username"], datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat()))

        conn.commit()
        conn.close()
        return JSONResponse(status_code=200, content={"message": f"User {username} created successfully", "userId": user_id, "success": True})
    except Exception as e:
        if conn:
            conn.close()
        return JSONResponse(status_code=500, content={"message": f"Internal server error: {str(e)}", "error": True})

@app.put("/v2/admin/users/{user_id}")
async def admin_update_user(user_id: str, user_data: dict, token_data: dict = Depends(verify_admin)):
    """Admin endpoint to update user"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    
    if not user:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")
    
    # Build update query dynamically
    updates = []
    params = []
    
    if "email" in user_data:
        updates.append("email = ?")
        params.append(user_data["email"])
    
    if "role" in user_data:
        updates.append("role = ?")
        params.append(user_data["role"])
    
    if "isActive" in user_data:
        updates.append("isActive = ?")
        params.append(1 if user_data["isActive"] else 0)
    
    if updates:
        params.append(user_id)
        query = f"UPDATE users SET {', '.join(updates)} WHERE id = ?"
        cursor.execute(query, params)
        conn.commit()
    
    conn.close()
    return {"message": "User updated successfully"}

@app.delete("/v2/admin/users/{user_id}")
async def admin_delete_user(user_id: str, token_data: dict = Depends(verify_admin)):
    """Admin endpoint to delete user"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    
    if not user:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")
    
    if user["role"] == "owner":
        conn.close()
        raise HTTPException(status_code=403, detail="Cannot delete owner account")
    
    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    
    return {"message": "User deleted successfully"}

@app.get("/v2/admin/reports")
async def admin_get_reports(page: int = 1, limit: int = 50, token_data: dict = Depends(verify_admin)):
    conn = get_db()
    cursor = conn.cursor()
    offset = (page - 1) * limit
    cursor.execute("SELECT * FROM reports ORDER BY timestamp DESC LIMIT ? OFFSET ?", (limit, offset))
    reports = [dict(row) for row in cursor.fetchall()]
    
    cursor.execute("SELECT COUNT(*) as total FROM reports")
    total = cursor.fetchone()["total"]
    
    conn.close()
    
    return {
        "reports": reports,
        "pagination": {
            "currentPage": page,
            "totalPages": (total + limit - 1) // limit if total else 1,
            "total": total
        }
    }

@app.get("/v2/admin/config")
async def admin_get_config(token_data: dict = Depends(verify_admin)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM settings")
    settings = {row["key"]: row["value"] for row in cursor.fetchall()}
    conn.close()
    
    # Convert string values to appropriate types
    return {
        "maxReportsPerUser": int(settings.get("maxReportsPerUser", "1000")),
        "maxBulkTargets": int(settings.get("maxBulkTargets", "200")),
        "maxPremiumBulkTargets": int(settings.get("maxPremiumBulkTargets", "500")),
        "apiTimeout": int(settings.get("apiTimeout", "30")),
        "rateLimitPerMinute": int(settings.get("rateLimitPerMinute", "60")),
        "maintenanceMode": settings.get("maintenanceMode", "false") == "true",
        "registrationEnabled": settings.get("registrationEnabled", "true") == "true",
        "requireApproval": settings.get("requireApproval", "true") == "true"
    }

@app.put("/v2/admin/config")
async def admin_update_config(config_data: dict, token_data: dict = Depends(verify_admin)):
    conn = get_db()
    cursor = conn.cursor()
    
    # Update each setting
    for key, value in config_data.items():
        # Convert boolean values to string
        if isinstance(value, bool):
            value = "true" if value else "false"
        else:
            value = str(value)
        
        cursor.execute("""
            INSERT OR REPLACE INTO settings (key, value, updated_at)
            VALUES (?, ?, ?)
        """, (key, value, datetime.now(timezone.utc).isoformat()))
    
    conn.commit()
    conn.close()
    
    return {"message": "Configuration updated successfully"}

@app.get("/v2/admin/logs")
async def admin_get_logs(limit: int = 100, token_data: dict = Depends(verify_admin)):
    return {"logs": []}

# Pending Accounts Review Routes
@app.get("/v2/admin/pending-accounts")
async def get_pending_accounts(token_data: dict = Depends(verify_admin)):
    """Get list of accounts pending approval"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM users WHERE isApproved = 0 ORDER BY createdAt DESC")
    pending_users = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    return {"pendingAccounts": pending_users, "total": len(pending_users)}

@app.post("/v2/admin/approve-account/{user_id}")
async def approve_account(user_id: str, token_data: dict = Depends(verify_admin)):
    """Approve a pending account"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    
    if not user:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")
    
    if user["isApproved"]:
        conn.close()
        raise HTTPException(status_code=400, detail="Account is already approved")
    
    cursor.execute('''
        UPDATE users 
        SET isApproved = 1, approvedBy = ?, approvedAt = ?
        WHERE id = ?
    ''', (token_data["username"], datetime.now(timezone.utc).isoformat(), user_id))
    
    conn.commit()
    conn.close()
    
    return {"message": f"Account {user['username']} approved successfully"}

@app.post("/v2/admin/reject-account/{user_id}")
async def reject_account(user_id: str, token_data: dict = Depends(verify_admin)):
    """Reject and delete a pending account"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    
    if not user:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")
    
    if user["isProtected"]:
        conn.close()
        raise HTTPException(status_code=403, detail="Cannot reject protected account")
    
    # Delete the user
    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
    cursor.execute("DELETE FROM credentials WHERE userId = ?", (user_id,))
    cursor.execute("DELETE FROM reports WHERE userId = ?", (user_id,))
    
    conn.commit()
    conn.close()
    
    return {"message": f"Account {user['username']} rejected and deleted"}

@app.put("/v2/admin/assign-role/{user_id}")
async def assign_role(user_id: str, role_data: dict, token_data: dict = Depends(verify_admin)):
    """Assign or change user role (user, premium, admin, owner)"""
    conn = get_db()
    cursor = conn.cursor()
    
    new_role = role_data.get("role", "").lower()
    
    if new_role not in ["user", "premium", "admin", "owner"]:
        conn.close()
        raise HTTPException(status_code=400, detail="Invalid role. Must be: user, premium, admin, or owner")
    
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    
    if not user:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")
    
    if user["isProtected"] and new_role != "owner":
        conn.close()
        raise HTTPException(status_code=403, detail="Cannot change role of protected owner account")
    
    cursor.execute("UPDATE users SET role = ? WHERE id = ?", (new_role, user_id))
    conn.commit()
    conn.close()
    
    return {"message": f"Role updated to {new_role} for user {user['username']}"}

# Blacklist Routes
@app.get("/v2/admin/blacklist")
async def get_blacklist(token_data: dict = Depends(verify_admin)):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM blacklist ORDER BY created_at DESC")
    blacklist = [dict(row) for row in cursor.fetchall()]
    
    cursor.execute("SELECT COUNT(*) as total FROM blacklist")
    total = cursor.fetchone()["total"]
    
    cursor.execute("SELECT SUM(blocked_attempts) as blocked FROM blacklist")
    blocked = cursor.fetchone()["blocked"] or 0
    
    conn.close()
    
    return {
        "blacklist": blacklist,
        "stats": {
            "total": total,
            "blocked": blocked
        }
    }

@app.post("/v2/admin/blacklist")
async def add_to_blacklist(data: dict, token_data: dict = Depends(verify_admin)):
    conn = get_db()
    cursor = conn.cursor()
    
    username = data.get("username", "").lower().strip()
    reason = data.get("reason", "")
    notes = data.get("notes", "")
    
    if not username or not reason:
        conn.close()
        raise HTTPException(status_code=400, detail="Username and reason are required")
    
    # Check if already blacklisted
    cursor.execute("SELECT * FROM blacklist WHERE username = ?", (username,))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="Account is already blacklisted")
    
    cursor.execute('''
        INSERT INTO blacklist (username, reason, notes, added_by, blocked_attempts, created_at)
        VALUES (?, ?, ?, ?, 0, ?)
    ''', (username, reason, notes, token_data["username"], datetime.now(timezone.utc).isoformat()))
    
    conn.commit()
    conn.close()
    
    return {"message": f"@{username} added to blacklist successfully"}

@app.delete("/v2/admin/blacklist/{username}")
async def remove_from_blacklist(username: str, token_data: dict = Depends(verify_admin)):
    conn = get_db()
    cursor = conn.cursor()
    
    username = username.lower().strip()
    
    cursor.execute("DELETE FROM blacklist WHERE username = ?", (username,))
    
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Account not found in blacklist")
    
    conn.commit()
    conn.close()
    
    return {"message": f"@{username} removed from blacklist"}

@app.delete("/v2/admin/logs")
async def admin_clear_logs(token_data: dict = Depends(verify_admin)):
    return {"message": "Logs cleared successfully"}

# Chat Routes
@app.get("/chat", response_class=HTMLResponse)
async def chat_page():
    """Serve chat page"""
    return FileResponse(os.path.join(FRONTEND_DIR, "chat.html"))

@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time chat"""
    # Get token from query params
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=1008)
        return
    
    try:
        # Verify token
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_info = {
            "user_id": payload["user_id"],
            "username": payload["username"],
            "role": payload["role"]
        }
        
        await manager.connect(websocket, user_info)
        
        # Send user joined notification
        await manager.broadcast({
            "type": "user_joined",
            "username": user_info["username"],
            "role": user_info["role"],
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        try:
            while True:
                # Receive message from client
                data = await websocket.receive_json()
                
                if data.get("type") == "message":
                    message_text = data.get("message", "").strip()
                    if message_text:
                        # Save message to database
                        conn = get_db()
                        cursor = conn.cursor()
                        
                        message_id = str(uuid.uuid4())
                        cursor.execute('''
                            INSERT INTO chat_messages (id, userId, username, role, message, timestamp)
                            VALUES (?, ?, ?, ?, ?, ?)
                        ''', (
                            message_id,
                            user_info["user_id"],
                            user_info["username"],
                            user_info["role"],
                            message_text,
                            datetime.now(timezone.utc).isoformat()
                        ))
                        conn.commit()
                        conn.close()
                        
                        # Broadcast message to all connected clients
                        await manager.broadcast({
                            "type": "message",
                            "id": message_id,
                            "username": user_info["username"],
                            "role": user_info["role"],
                            "message": message_text,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        })
        except WebSocketDisconnect:
            manager.disconnect(websocket)
            await manager.broadcast({
                "type": "user_left",
                "username": user_info["username"],
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
    except jwt.InvalidTokenError:
        await websocket.close(code=1008)

@app.get("/v2/chat/history")
async def get_chat_history(limit: int = 50, token_data: dict = Depends(verify_token)):
    """Get recent chat messages"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, username, role, message, timestamp
        FROM chat_messages
        ORDER BY timestamp DESC
        LIMIT ?
    ''', (limit,))
    
    messages = [dict(row) for row in cursor.fetchall()]
    messages.reverse()  # Show oldest first
    
    conn.close()
    
    return {"messages": messages}

@app.get("/v2/chat/users")
async def get_online_users(token_data: dict = Depends(verify_token)):
    """Get list of currently online users"""
    online_users = [
        {
            "username": conn["user"]["username"],
            "role": conn["user"]["role"]
        }
        for conn in manager.active_connections
    ]
    
    return {"users": online_users, "count": len(online_users)}

@app.delete("/v2/admin/chat/clear")
async def clear_chat_history(token_data: dict = Depends(verify_admin)):
    """Clear all chat messages (admin only)"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM chat_messages")
    conn.commit()
    conn.close()
    
    return {"message": "Chat history cleared successfully"}

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting SWATNFO Backend...")
    uvicorn.run(app, host="0.0.0.0", port=8000)


