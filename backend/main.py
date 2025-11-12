# SWATNFO Instagram Report Bot - Backend API (SQLite Version)
# Made by SWATNFO - d3sapiv2

from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime, timedelta, timezone
from contextlib import asynccontextmanager
from urllib.parse import unquote
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
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
    count: Optional[int] = 1  # Number of times to report (1-20)

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
            lastLoginAt TEXT,
            reportCount INTEGER DEFAULT 0,
            failedLoginAttempts INTEGER DEFAULT 0,
            lastFailedLogin TEXT,
            accountLockedUntil TEXT,
            isPremium INTEGER DEFAULT 0,
            premiumExpiresAt TEXT,
            registrationIP TEXT
        )
    ''')
    
    # Credentials table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS credentials (
            userId TEXT PRIMARY KEY,
            sessionId TEXT,
            csrfToken TEXT,
            updatedAt TEXT,
            expiresAt TEXT
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

# Database Migration - Add missing columns to existing databases
def migrate_db():
    """Add any missing columns to existing tables"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if columns exist in users table
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'lastLoginAt' not in columns:
            print("🔧 Adding lastLoginAt column to users table...")
            cursor.execute("ALTER TABLE users ADD COLUMN lastLoginAt TEXT")
            conn.commit()
            print("✅ lastLoginAt column added successfully")
        
        if 'isPremium' not in columns:
            print("🔧 Adding isPremium column to users table...")
            cursor.execute("ALTER TABLE users ADD COLUMN isPremium INTEGER DEFAULT 0")
            conn.commit()
            print("✅ isPremium column added successfully")
        
        if 'premiumExpiresAt' not in columns:
            print("🔧 Adding premiumExpiresAt column to users table...")
            cursor.execute("ALTER TABLE users ADD COLUMN premiumExpiresAt TEXT")
            conn.commit()
            print("✅ premiumExpiresAt column added successfully")
        
        if 'registrationIP' not in columns:
            print("🔧 Adding registrationIP column to users table...")
            cursor.execute("ALTER TABLE users ADD COLUMN registrationIP TEXT")
            conn.commit()
            print("✅ registrationIP column added successfully")
        
        # Check if columns exist in credentials table
        cursor.execute("PRAGMA table_info(credentials)")
        cred_columns = [column[1] for column in cursor.fetchall()]
        
        if 'expiresAt' not in cred_columns:
            print("🔧 Adding expiresAt column to credentials table...")
            cursor.execute("ALTER TABLE credentials ADD COLUMN expiresAt TEXT")
            conn.commit()
            print("✅ expiresAt column added successfully")
        
    except Exception as e:
        print(f"⚠️ Migration warning: {e}")
    finally:
        conn.close()

# Lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    migrate_db()  # Run database migrations
    
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

# CORS - Secure production configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://18.222.136.234:8000",
        "http://18.222.136.234",
        "https://18.222.136.234:8000",
        "https://18.222.136.234",
        "http://localhost:8000",
        "http://127.0.0.1:8000"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"]
)

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

def is_premium_active(user_data: dict) -> bool:
    """Check if user has active premium (including trial period)"""
    # Handle sqlite3.Row objects
    try:
        is_premium = user_data["isPremium"] if "isPremium" in user_data.keys() else 0
    except (KeyError, AttributeError):
        return False
    
    if not is_premium:
        return False
    
    # If no expiration date, premium is permanent (for manually upgraded users)
    try:
        premium_expires_at = user_data["premiumExpiresAt"] if "premiumExpiresAt" in user_data.keys() else None
    except (KeyError, AttributeError):
        return True
    
    if not premium_expires_at:
        return True
    
    # Check if premium trial/subscription hasn't expired yet
    try:
        expires_at = datetime.fromisoformat(premium_expires_at)
        return datetime.now(timezone.utc) < expires_at
    except:
        return False

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
# Maintenance Mode Middleware
@app.middleware("http")
async def maintenance_mode_middleware(request, call_next):
    # Get the path
    path = request.url.path
    
    # Skip maintenance check for:
    # - Admin pages (/admin, /admin.html, /admin/)
    # - Login and register pages (so admins can log in)
    # - All admin API endpoints (/v2/admin/*)
    # - All auth endpoints (/v2/auth/*)
    # - All user endpoints (/v2/user/*)
    # - TOS page
    # - Static files (CSS, JS, assets)
    if (path.startswith("/admin") or 
        path in ["/login.html", "/register.html", "/login", "/register"] or
        path.startswith("/v2/admin") or
        path.startswith("/v2/auth") or
        path.startswith("/v2/user") or
        path == "/tos.html" or
        path.startswith(("/css", "/js", "/assets"))):
        return await call_next(request)
    
    # Check if maintenance mode is enabled
    if is_maintenance_mode():
        return get_maintenance_page()
    
    return await call_next(request)

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
async def register(user: UserRegister, request: Request):
    conn = None
    try:
        # Check if registration is enabled
        temp_conn = get_db()
        temp_cursor = temp_conn.cursor()
        temp_cursor.execute("SELECT value FROM settings WHERE key = 'registrationEnabled'")
        reg_setting = temp_cursor.fetchone()
        temp_conn.close()
        
        if reg_setting and reg_setting["value"] == "false":
            return JSONResponse(
                status_code=403,
                content={"message": "Registration is currently disabled by administrators", "error": True}
            )
        
        # Get client IP
        client_ip = request.client.host
        
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
        
        # No free premium trial - all new users start as regular users
        is_premium = 0
        premium_expires_at = None
        
        cursor.execute('''
            INSERT INTO users (id, username, email, password, role, isActive, isProtected, isApproved, approvedBy, approvedAt, createdAt, reportCount, failedLoginAttempts, lastFailedLogin, accountLockedUntil, isPremium, premiumExpiresAt, registrationIP)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, user.username, email, hashed_pw, "user", 1, 0, is_approved, approved_by, approved_at, datetime.now(timezone.utc).isoformat(), 0, 0, None, None, is_premium, premium_expires_at, client_ip))
        
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
    
    # Reset failed login attempts and update last login on successful login
    try:
        cursor.execute(
            "UPDATE users SET failedLoginAttempts = 0, lastFailedLogin = NULL, accountLockedUntil = NULL, lastLoginAt = ? WHERE id = ?", 
            (datetime.now(timezone.utc).isoformat(), user["id"])
        )
    except sqlite3.OperationalError:
        # Fallback if lastLoginAt column doesn't exist yet
        cursor.execute(
            "UPDATE users SET failedLoginAttempts = 0, lastFailedLogin = NULL, accountLockedUntil = NULL WHERE id = ?", 
            (user["id"],)
        )
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
        return {"credentials": None, "configured": False, "expired": False}
    
    # Check if credentials are expired
    is_expired = False
    days_until_expiry = None
    
    # Convert Row to dict for easier access
    cred_dict = dict(cred)
    
    if cred_dict.get("expiresAt"):
        expires_at = datetime.fromisoformat(cred_dict["expiresAt"])
        now = datetime.now(timezone.utc)
        
        if now > expires_at:
            is_expired = True
        else:
            days_until_expiry = (expires_at - now).days
    
    return {
        "credentials": {
            "sessionId": cred_dict["sessionId"],
            "csrfToken": cred_dict["csrfToken"],
            "isValid": not is_expired,
            "expiresAt": cred_dict.get("expiresAt"),
            "daysUntilExpiry": days_until_expiry
        },
        "configured": True,
        "expired": is_expired
    }

@app.post("/v2/credentials")
async def save_credentials(creds: Credentials, token_data: dict = Depends(verify_token)):
    """Save Instagram cookies (sessionid and csrftoken) - EXACT swatnfobest.py approach"""
    try:
        # URL decode the credentials in case they were copied encoded
        decoded_session = unquote(creds.sessionId)
        decoded_csrf = unquote(creds.csrfToken)
        
        print(f"💾 Saving credentials for user {token_data['user_id']}")
        print(f"   SessionId (raw): {creds.sessionId[:20]}... (length: {len(creds.sessionId)})")
        print(f"   SessionId (decoded): {decoded_session[:20]}... (length: {len(decoded_session)})")
        print(f"   CsrfToken: {decoded_csrf[:20]}... (length: {len(decoded_csrf)})")
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Set expiry to 30 days from now
        expires_at = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        
        cursor.execute("SELECT * FROM credentials WHERE userId = ?", (token_data["user_id"],))
        existing = cursor.fetchone()
        
        if existing:
            print(f"   📝 Updating existing credentials")
            cursor.execute('''
                UPDATE credentials SET sessionId = ?, csrfToken = ?, updatedAt = ?, expiresAt = ?
                WHERE userId = ?
            ''', (decoded_session, decoded_csrf, datetime.now(timezone.utc).isoformat(), expires_at, token_data["user_id"]))
        else:
            print(f"   ➕ Creating new credentials")
            cursor.execute('''
                INSERT INTO credentials (userId, sessionId, csrfToken, updatedAt, expiresAt)
                VALUES (?, ?, ?, ?, ?)
            ''', (token_data["user_id"], decoded_session, decoded_csrf, datetime.now(timezone.utc).isoformat(), expires_at))
        
        conn.commit()
        
        # Verify the save
        cursor.execute("SELECT * FROM credentials WHERE userId = ?", (token_data["user_id"],))
        saved = cursor.fetchone()
        if saved:
            print(f"   ✅ Verified saved - SessionId: {saved['sessionId'][:20]}...")
        
        conn.close()
        
        return {"success": True, "message": "Credentials saved successfully"}
        
    except Exception as e:
        print(f"❌ Error saving credentials: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error saving credentials: {str(e)}")

@app.post("/v2/credentials/test")
async def test_credentials(token_data: dict = Depends(verify_token)):
    """Test credentials are saved (no actual Instagram API test - just check if they exist)"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM credentials WHERE userId = ?", (token_data["user_id"],))
    cred = cursor.fetchone()
    conn.close()
    
    if not cred:
        return {"valid": False, "message": "No credentials configured"}
    
    return {"valid": True, "message": "Credentials are saved"}

# Helper function: Get target ID (EXACT from swatnfobest.py)
def get_target_id(target_username: str, sessionid: str, csrftoken: str) -> str:
    """Get Instagram user ID from username - EXACT swatnfobest.py logic with proxy support"""
    proxy = get_random_proxy()
    
    try:
        # Method 1: API lookup
        print(f"   🔍 Method 1: API lookup via proxy")
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
                "signed_body": f'35a2d547d3b6ff400f713948cdffe0b789a903f86117eb6e2f3e573079b2f038.{{"q":"{target_username}"}}'
            },
            proxies=proxy,
            timeout=10
        )
        
        print(f"   Method 1 Status: {r2.status_code}")
        if 'No users found' not in r2.text and '"spam":true' not in r2.text:
            try:
                target_id = str(r2.json()['user_id'])
                print(f"   ✅ Method 1 success: {target_id}")
                return target_id
            except KeyError:
                print(f"   ❌ Method 1 KeyError")
                pass
        else:
            print(f"   ❌ Method 1: No users found or spam")
        
        # Method 2: Web scraping
        print(f"   🔍 Method 2: Web scraping via proxy")
        adv_search = requests.get(
            f'https://www.instagram.com/{target_username}',
            headers={
                'Host': 'www.instagram.com',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/110.0',
                'Cookie': f'csrftoken={csrftoken}',
            },
            proxies=proxy,
            timeout=10
        )
        
        print(f"   Method 2 Status: {adv_search.status_code}")
        import re
        patterns = [
            r'"profile_id":"(.*?)"',
            r'"page_id":"profilePage_(.*?)"'
        ]
        
        for pattern in patterns:
            match = re.findall(pattern, adv_search.text)
            if match:
                print(f"   ✅ Method 2 success: {match[0]}")
                return match[0]
        
        print(f"   ❌ Method 2: No pattern match")
        
        # Method 3: Web API
        print(f"   🔍 Method 3: Web API via proxy")
        adv_search2 = requests.get(
            f'https://www.instagram.com/api/v1/users/web_profile_info/?username={target_username}',
            headers={
                'Host': 'www.instagram.com',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/110.0',
                'X-CSRFToken': csrftoken,
                'X-IG-App-ID': '936619743392459',
                'Cookie': f'sessionid={sessionid}'
            },
            proxies=proxy,
            timeout=10
        )
        
        print(f"   Method 3 Status: {adv_search2.status_code}")
        if adv_search2.status_code == 200:
            target_id = adv_search2.json()['data']['user']['id']
            print(f"   ✅ Method 3 success: {target_id}")
            return target_id
        else:
            print(f"   ❌ Method 3: Status {adv_search2.status_code}")
            print(f"   Response: {adv_search2.text[:200]}")
        
    except Exception as e:
        print(f"   ❌ Error getting target ID: {str(e)}")
        return None
    
    return None

# Helper function: Send single report (EXACT from swatnfobest.py)
def instagram_send_report(target_id: str, sessionid: str, csrftoken: str, method: str = "spam") -> bool:
    """Send a single report to Instagram - EXACT swatnfobest.py logic with proxy support"""
    proxy = get_random_proxy()
    
    try:
        # Map method names to reason_id and additional data (from swatnfobest.py)
        method_config = {
            "spam": {"reason_id": 1, "data": ""},
            "self_injury": {"reason_id": 2, "data": ""},
            "violent_threat": {"reason_id": 3, "data": ""},
            "hate_speech": {"reason_id": 4, "data": ""},
            "nudity": {"reason_id": 5, "data": ""},
            "bullying": {"reason_id": 6, "data": ""},
            "impersonation_me": {"reason_id": 1, "data": ""},
            "tmnaofcl": {"reason_id": 1, "data": "&action_type=celebrity&celebrity_username=tmnaofcl"},
            "sale_illegal": {"reason_id": 7, "data": ""},
            "violence": {"reason_id": 8, "data": ""},
            "intellectual_property": {"reason_id": 9, "data": ""},
        }
        
        config = method_config.get(method, {"reason_id": 1, "data": ""})
        reason_id = config["reason_id"]
        extra_data = config["data"]
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/110.0",
            "Host": "i.instagram.com",
            'cookie': f"sessionid={sessionid}",
            "X-CSRFToken": csrftoken,
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
        }
        
        data = f'source_name=&reason_id={reason_id}&frx_context={extra_data}'
        
        print(f"   📤 Sending report via proxy - method: {method}, reason_id: {reason_id}")
        r3 = requests.post(
            f"https://i.instagram.com/users/{target_id}/flag/",
            headers=headers,
            data=data,
            allow_redirects=False,
            proxies=proxy,
            timeout=10
        )
        
        print(f"   Report Status: {r3.status_code}")
        if r3.status_code == 429:
            print("[ERROR] Rate limited")
            return False
        elif r3.status_code == 500:
            print("[ERROR] Target not found")
            return False
        elif r3.status_code in [200, 302]:
            print(f"   ✅ Report sent successfully")
            return True
        else:
            print(f"   ⚠️  Unexpected status but treating as success: {r3.status_code}")
            return True  # Sometimes reports work even with unexpected status codes
            
    except requests.exceptions.TooManyRedirects:
        print(f"   ✅ Too many redirects (treated as success)")
        return True
    except Exception as e:
        print(f"   ❌ Error sending report: {str(e)}")
        return False

# Reporting Routes
@app.post("/v2/reports/send")
async def send_report(report: ReportRequest, token_data: dict = Depends(verify_token), is_bulk: bool = False):
    """Send Instagram report - Now supports 1-20 reports per target"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Validate count (1-20)
    report_count = min(max(report.count, 1), 20)
    
    # Get user info to check role and premium status
    cursor.execute("SELECT role, isPremium, premiumExpiresAt FROM users WHERE id = ?", (token_data["user_id"],))
    user = cursor.fetchone()
    user_role = user["role"] if user else "user"
    
    # Check if user has active premium (including trial)
    has_active_premium = is_premium_active(user) if user else False
    
    # Check if bulk reporting is allowed (premium users, active premium trial, or admin/owner)
    if is_bulk and user_role not in ["admin", "owner"] and not has_active_premium:
        conn.close()
        raise HTTPException(
            status_code=403, 
            detail="Bulk reporting is exclusive to Premium users. Contact SWATNFO or Xefi for payment to upgrade your account."
        )
    
    # Check daily report limit for regular users without active premium (100 reports per day)
    if user_role == "user" and not has_active_premium:
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
        cursor.execute("UPDATE blacklist SET blocked_attempts = blocked_attempts + 1 WHERE username = ?", (report.target.lower(),))
        conn.commit()
        conn.close()
        raise HTTPException(status_code=403, detail=f"Target @{report.target} is blacklisted and cannot be reported")
    
    # Get credentials
    cursor.execute("SELECT * FROM credentials WHERE userId = ?", (token_data["user_id"],))
    cred = cursor.fetchone()
    
    if not cred:
        conn.close()
        raise HTTPException(status_code=400, detail="Please configure Instagram credentials first")
    
    print(f"📤 Reporting @{report.target} {report_count}x using method: {report.method}")
    print(f"   Using SessionId: {cred['sessionId'][:20]}... (length: {len(cred['sessionId'])})")
    print(f"   Using CsrfToken: {cred['csrfToken'][:20]}... (length: {len(cred['csrfToken'])})")
    
    # Check 3-minute cooldown for free users on same target (removed - now they can report 20x)
    # if not is_bulk and user_role == "user":
    #     three_minutes_ago = (datetime.now(timezone.utc) - timedelta(minutes=3)).isoformat()
    #     cursor.execute(
    #         "SELECT timestamp FROM reports WHERE userId = ? AND target = ? AND timestamp >= ? ORDER BY timestamp DESC LIMIT 1",
    #         (token_data["user_id"], report.target, three_minutes_ago)
    #     )
    #     recent_report = cursor.fetchone()
    #     
    #     if recent_report:
    #         last_report_time = datetime.fromisoformat(recent_report["timestamp"])
    #         time_diff = datetime.now(timezone.utc) - last_report_time
    #         seconds_remaining = 180 - int(time_diff.total_seconds())
    #         minutes_remaining = seconds_remaining // 60
    #         secs_remaining = seconds_remaining % 60
    #         
    #         conn.close()
    #         raise HTTPException(
    #             status_code=400, 
    #             detail=f"Please wait {minutes_remaining}m {secs_remaining}s before reporting @{report.target} again. Upgrade to Premium for unlimited bulk reporting."
    #         )
    
    # Get target ID using swatnfobest.py logic
    print(f"🔍 Looking up target ID for @{report.target}")
    target_id = get_target_id(report.target, cred["sessionId"], cred["csrfToken"])
    
    if not target_id:
        print(f"❌ Failed to get target ID for @{report.target} - all 3 methods failed")
        conn.close()
        raise HTTPException(status_code=404, detail=f"Could not find user @{report.target}. User may be private, deleted, or credentials may be invalid. Check PM2 logs for details.")
    
    # Send reports multiple times (1-20)
    successful_reports = 0
    failed_reports = 0
    
    for i in range(report_count):
        print(f"   📤 Sending report {i+1}/{report_count}")
        success = instagram_send_report(target_id, cred["sessionId"], cred["csrfToken"], report.method)
        
        # Log each report
        report_id = str(uuid.uuid4())
        cursor.execute('''
            INSERT INTO reports (id, userId, username, target, targetId, method, status, type, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (report_id, token_data["user_id"], token_data["username"], report.target, 
              target_id, report.method, 
              "success" if success else "failed", "single", 
              datetime.now(timezone.utc).isoformat()))
        
        if success:
            successful_reports += 1
            cursor.execute("UPDATE users SET reportCount = reportCount + 1 WHERE id = ?", (token_data["user_id"],))
        else:
            failed_reports += 1
        
        # 1.5 second delay between reports
        if i < report_count - 1:
            time.sleep(1.5)
    
    conn.commit()
    conn.close()
    
    print(f"✅ Completed: {successful_reports}/{report_count} successful")
    
    if successful_reports > 0:
        return {
            "success": True, 
            "message": f"{successful_reports}/{report_count} reports sent successfully",
            "successful": successful_reports,
            "failed": failed_reports
        }
    else:
        return {
            "success": False, 
            "message": "All reports failed",
            "successful": 0,
            "failed": failed_reports
        }

@app.post("/v2/reports/bulk")
async def send_bulk_report(bulk_data: dict, token_data: dict = Depends(verify_token)):
    """Send bulk Instagram reports with 4-second delay between each target"""
    targets = bulk_data.get("targets", [])
    method = bulk_data.get("method", "spam")
    count = bulk_data.get("count", 1)  # Number of reports per target (1-15)
    
    if not targets:
        raise HTTPException(status_code=400, detail="No targets provided")
    
    # Validate count
    if count < 1 or count > 15:
        raise HTTPException(status_code=400, detail="Count must be between 1 and 15")
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Get user info to check role and premium status
    cursor.execute("SELECT role, isPremium, premiumExpiresAt FROM users WHERE id = ?", (token_data["user_id"],))
    user = cursor.fetchone()
    user_role = user["role"] if user else "user"
    
    # Check if user has active premium (including trial)
    has_active_premium = is_premium_active(user) if user else False
    
    # Check if bulk reporting is allowed (premium users, active premium trial, or admin/owner)
    if user_role not in ["admin", "owner"] and not has_active_premium:
        conn.close()
        raise HTTPException(
            status_code=403, 
            detail="Bulk reporting is exclusive to Premium users. Contact SWATNFO or Xefi for payment to upgrade your account."
        )
    
    # Check bulk target limits
    max_bulk = 500 if user_role in ["admin", "owner"] else 200
    if len(targets) > max_bulk:
        conn.close()
        raise HTTPException(status_code=400, detail=f"Maximum {max_bulk} targets allowed per bulk report")
    
    # Get credentials
    cursor.execute("SELECT * FROM credentials WHERE userId = ?", (token_data["user_id"],))
    cred = cursor.fetchone()
    
    if not cred:
        conn.close()
        raise HTTPException(status_code=400, detail="Please configure Instagram credentials first")
    
    print(f"📦 BULK REPORT: {len(targets)} targets x {count} reports each, method: {method}")
    print(f"   User: {token_data['username']} ({user_role})")
    print(f"   1.5-second delay between each report")
    
    results = {
        "total": len(targets),
        "successful": 0,
        "failed": 0,
        "blacklisted": 0,
        "details": []
    }
    
    for idx, target in enumerate(targets, 1):
        target = target.strip().replace("@", "")
        
        if not target:
            continue
        
        print(f"\n   [{idx}/{len(targets)}] Processing @{target}")
        
        # Check if target is blacklisted
        cursor.execute("SELECT * FROM blacklist WHERE username = ?", (target.lower(),))
        blacklisted = cursor.fetchone()
        
        if blacklisted:
            print(f"   ⛔ @{target} is blacklisted")
            cursor.execute("UPDATE blacklist SET blocked_attempts = blocked_attempts + 1 WHERE username = ?", (target.lower(),))
            conn.commit()
            results["blacklisted"] += 1
            results["details"].append({
                "target": target,
                "status": "blacklisted",
                "message": "Target is blacklisted"
            })
            
            # 4-second delay even for blacklisted targets
            if idx < len(targets):
                print(f"   ⏱️  Waiting 4 seconds before next target...")
                time.sleep(4)
            continue
        
        # Get target ID
        target_id = get_target_id(target, cred["sessionId"], cred["csrfToken"])
        
        if not target_id:
            print(f"   ❌ @{target} not found")
            results["failed"] += 1
            results["details"].append({
                "target": target,
                "status": "failed",
                "message": "User not found or private"
            })
            
            # Log failed report
            report_id = str(uuid.uuid4())
            cursor.execute('''
                INSERT INTO reports (id, userId, username, target, targetId, method, status, type, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (report_id, token_data["user_id"], token_data["username"], target, 
                  None, method, "failed", "bulk", datetime.now(timezone.utc).isoformat()))
            conn.commit()
            
            # 2-second delay before next target
            if idx < len(targets):
                print(f"   ⏱️  Waiting 2 seconds before next target...")
                time.sleep(2)
            continue
        
        # Send multiple reports for this target (count times)
        target_success = 0
        target_failed = 0
        
        for report_num in range(count):
            success = instagram_send_report(target_id, cred["sessionId"], cred["csrfToken"], method)
            
            # Log report
            report_id = str(uuid.uuid4())
            cursor.execute('''
                INSERT INTO reports (id, userId, username, target, targetId, method, status, type, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (report_id, token_data["user_id"], token_data["username"], target, 
                  target_id, method, "success" if success else "failed", "bulk", 
                  datetime.now(timezone.utc).isoformat()))
            
            if success:
                cursor.execute("UPDATE users SET reportCount = reportCount + 1 WHERE id = ?", (token_data["user_id"],))
                target_success += 1
            else:
                target_failed += 1
            
            # 1.5 second delay between reports for same target (except last report)
            if report_num < count - 1:
                time.sleep(1.5)
        
        # Update results
        if target_success > 0:
            results["successful"] += 1
            results["details"].append({
                "target": target,
                "status": "success",
                "message": f"{target_success}/{count} reports sent successfully"
            })
            print(f"   ✅ @{target} - {target_success}/{count} reports sent")
        else:
            results["failed"] += 1
            results["details"].append({
                "target": target,
                "status": "failed",
                "message": f"All {count} reports failed"
            })
            print(f"   ❌ @{target} - all {count} reports failed")
        
        conn.commit()
        
        # 2-second delay before next target (except for last target)
        if idx < len(targets):
            print(f"   ⏱️  Waiting 2 seconds before next target...")
            time.sleep(2)
    
    conn.close()
    
    print(f"\n✅ BULK REPORT COMPLETE: {results['successful']}/{results['total']} successful")
    
    return {
        "success": True,
        "message": f"Bulk report completed: {results['successful']}/{results['total']} successful",
        "results": results
    }

@app.post("/v2/reports/mass")
async def send_mass_report(mass_data: dict, token_data: dict = Depends(verify_token)):
    """Mass report feature: Report same target up to 200 times with multi-threading (PREMIUM ONLY)"""
    target = mass_data.get("target", "").strip().replace("@", "")
    count = mass_data.get("count", 1)
    method = mass_data.get("method", "spam")
    
    if not target:
        raise HTTPException(status_code=400, detail="No target provided")
    
    # Validate count (1-200)
    count = min(max(count, 1), 200)
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Get user info - PREMIUM ONLY
    cursor.execute("SELECT role FROM users WHERE id = ?", (token_data["user_id"],))
    user = cursor.fetchone()
    user_role = user["role"] if user else "user"
    
    # Check if premium/admin/owner
    if user_role not in ["premium", "admin", "owner"]:
        conn.close()
        raise HTTPException(
            status_code=403, 
            detail="Mass reporting is exclusive to Premium users. Contact SWATNFO or Xefi for payment to upgrade your account."
        )
    
    # Check if target is blacklisted
    cursor.execute("SELECT * FROM blacklist WHERE username = ?", (target.lower(),))
    blacklisted = cursor.fetchone()
    
    if blacklisted:
        cursor.execute("UPDATE blacklist SET blocked_attempts = blocked_attempts + 1 WHERE username = ?", (target.lower(),))
        conn.commit()
        conn.close()
        raise HTTPException(status_code=403, detail=f"Target @{target} is blacklisted and cannot be reported")
    
    # Get credentials
    cursor.execute("SELECT * FROM credentials WHERE userId = ?", (token_data["user_id"],))
    cred = cursor.fetchone()
    
    if not cred:
        conn.close()
        raise HTTPException(status_code=400, detail="Please configure Instagram credentials first")
    
    print(f"🚀 MASS REPORT: @{target} x{count} times using method: {method}")
    print(f"   User: {token_data['username']} ({user_role})")
    print(f"   Using multi-threading for speed")
    
    # Get target ID
    target_id = get_target_id(target, cred["sessionId"], cred["csrfToken"])
    
    if not target_id:
        print(f"❌ Failed to get target ID for @{target}")
        conn.close()
        raise HTTPException(status_code=404, detail=f"Could not find user @{target}. User may be private, deleted, or credentials may be invalid.")
    
    # Worker function for threading
    def send_single_mass_report(report_num: int) -> dict:
        """Send a single report (runs in thread)"""
        try:
            success = instagram_send_report(target_id, cred["sessionId"], cred["csrfToken"], method)
            
            # Log to database
            report_id = str(uuid.uuid4())
            temp_conn = get_db()
            temp_cursor = temp_conn.cursor()
            temp_cursor.execute('''
                INSERT INTO reports (id, userId, username, target, targetId, method, status, type, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (report_id, token_data["user_id"], token_data["username"], target, 
                  target_id, method, "success" if success else "failed", "mass", 
                  datetime.now(timezone.utc).isoformat()))
            
            if success:
                temp_cursor.execute("UPDATE users SET reportCount = reportCount + 1 WHERE id = ?", (token_data["user_id"],))
            
            temp_conn.commit()
            temp_conn.close()
            
            return {"report_num": report_num, "success": success}
        except Exception as e:
            print(f"   ❌ Thread {report_num} error: {e}")
            return {"report_num": report_num, "success": False, "error": str(e)}
    
    # Use ThreadPoolExecutor for parallel reporting with optimized thread count
    max_workers = 20  # Increased from 10 to 20 for faster mass reporting
    successful = 0
    failed = 0
    
    print(f"   🚀 Starting {max_workers} parallel threads...")
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        futures = {executor.submit(send_single_mass_report, i): i for i in range(1, count + 1)}
        
        # Process results as they complete
        for future in as_completed(futures):
            result = future.result()
            if result["success"]:
                successful += 1
                print(f"   ✅ Report {result['report_num']}/{count} sent")
            else:
                failed += 1
                print(f"   ❌ Report {result['report_num']}/{count} failed")
    
    conn.close()
    
    print(f"\n🎯 MASS REPORT COMPLETE: {successful}/{count} successful")
    
    return {
        "success": True,
        "message": f"Mass report completed: {successful}/{count} reports sent successfully",
        "target": target,
        "total": count,
        "successful": successful,
        "failed": failed
    }

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
    
    # Get total count for pagination (considering filters)
    count_query = "SELECT COUNT(*) as count FROM reports WHERE userId = ?"
    count_params = [token_data["user_id"]]
    
    if status != "all":
        count_query += " AND status = ?"
        count_params.append(status)
    if method != "all":
        count_query += " AND method = ?"
        count_params.append(method)
    if search:
        count_query += " AND target LIKE ?"
        count_params.append(f"%{search}%")
    
    cursor.execute(count_query, count_params)
    filtered_total = cursor.fetchone()["count"]
    
    # Get stats
    cursor.execute("SELECT COUNT(*) as total FROM reports WHERE userId = ?", (token_data["user_id"],))
    total_reports = cursor.fetchone()["total"]
    
    cursor.execute("SELECT COUNT(*) as success FROM reports WHERE userId = ? AND status = 'success'", (token_data["user_id"],))
    success_count = cursor.fetchone()["success"]
    
    cursor.execute("SELECT COUNT(*) as failed FROM reports WHERE userId = ? AND status = 'failed'", (token_data["user_id"],))
    failed_count = cursor.fetchone()["failed"]
    
    conn.close()
    
    import math
    total_pages = math.ceil(filtered_total / limit) if filtered_total > 0 else 1
    
    return {
        "reports": reports,
        "stats": {
            "total": total_reports,
            "successful": success_count,
            "failed": failed_count
        },
        "pagination": {
            "currentPage": page,
            "totalPages": total_pages,
            "pageSize": limit,
            "total": filtered_total
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
    
    # Count users who logged in today
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    cursor.execute("SELECT COUNT(*) as active FROM users WHERE lastLoginAt >= ?", (today,))
    active_today = cursor.fetchone()["active"]
    
    conn.close()
    
    return {
        "totalUsers": total_users,
        "totalReports": total_reports,
        "successRate": round(success_rate, 1),
        "activeToday": active_today
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
    
    # Only owners can assign owner role
    if new_role == "owner" and token_data["role"] != "owner":
        conn.close()
        raise HTTPException(status_code=403, detail="Only owners can assign owner role")
    
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

# Maintenance Mode Checker
def is_maintenance_mode() -> bool:
    """Check if maintenance mode is enabled"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = 'maintenanceMode'")
        result = cursor.fetchone()
        conn.close()
        return result and result["value"] == "true"
    except:
        return False

def get_maintenance_page() -> HTMLResponse:
    """Return beautiful maintenance page"""
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Under Maintenance - SWATNFO</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #0f0f1e 0%, #1a1a2e 50%, #16213e 100%);
                color: white;
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                overflow: hidden;
                position: relative;
            }
            
            .stars {
                position: absolute;
                width: 100%;
                height: 100%;
                overflow: hidden;
            }
            
            .star {
                position: absolute;
                background: white;
                border-radius: 50%;
                animation: twinkle 3s infinite;
            }
            
            @keyframes twinkle {
                0%, 100% { opacity: 0.3; }
                50% { opacity: 1; }
            }
            
            .container {
                text-align: center;
                z-index: 10;
                max-width: 600px;
                padding: 40px;
                background: rgba(26, 26, 46, 0.8);
                border-radius: 20px;
                border: 2px solid rgba(168, 85, 247, 0.3);
                box-shadow: 0 20px 60px rgba(168, 85, 247, 0.2);
                backdrop-filter: blur(10px);
            }
            
            .logo {
                font-size: 80px;
                margin-bottom: 20px;
                animation: pulse 2s ease-in-out infinite;
            }
            
            @keyframes pulse {
                0%, 100% { transform: scale(1); }
                50% { transform: scale(1.1); }
            }
            
            h1 {
                font-size: 2.5em;
                margin-bottom: 20px;
                background: linear-gradient(135deg, #a855f7 0%, #e879f9 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            }
            
            .subtitle {
                font-size: 1.2em;
                color: #999;
                margin-bottom: 30px;
            }
            
            .features {
                margin: 30px 0;
                padding: 20px;
                background: rgba(168, 85, 247, 0.1);
                border-radius: 12px;
                border: 1px solid rgba(168, 85, 247, 0.2);
            }
            
            .feature-item {
                padding: 10px;
                color: #e879f9;
                font-size: 1.1em;
            }
            
            .spinner {
                margin: 30px auto;
                width: 60px;
                height: 60px;
                border: 4px solid rgba(168, 85, 247, 0.2);
                border-top: 4px solid #a855f7;
                border-radius: 50%;
                animation: spin 1s linear infinite;
            }
            
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            
            .message {
                font-size: 1.1em;
                color: #ccc;
                line-height: 1.6;
            }
            
            .brand {
                margin-top: 40px;
                font-size: 0.9em;
                color: #666;
            }
        </style>
    </head>
    <body>
        <div class="stars" id="stars"></div>
        
        <div class="container">
            <div class="logo">🔧</div>
            <h1>Under Maintenance</h1>
            <p class="subtitle">We're making things better!</p>
            
            <div class="features">
                <div class="feature-item">✨ New Features Coming</div>
                <div class="feature-item">⚡ Performance Improvements</div>
                <div class="feature-item">🔒 Security Enhancements</div>
            </div>
            
            <div class="spinner"></div>
            
            <p class="message">
                We're currently performing scheduled maintenance to bring you<br>
                exciting new updates and improvements.<br><br>
                We'll be back online shortly. Thank you for your patience!
            </p>
            
            <div class="brand">
                <strong>SWATNFO</strong> | Instagram Report Bot v2
            </div>
        </div>
        
        <script>
            // Create stars
            const starsContainer = document.getElementById('stars');
            for (let i = 0; i < 100; i++) {
                const star = document.createElement('div');
                star.className = 'star';
                star.style.width = Math.random() * 3 + 'px';
                star.style.height = star.style.width;
                star.style.left = Math.random() * 100 + '%';
                star.style.top = Math.random() * 100 + '%';
                star.style.animationDelay = Math.random() * 3 + 's';
                starsContainer.appendChild(star);
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)

# Advanced Admin Features Endpoints
@app.post("/v2/admin/backup")
async def backup_database(token_data: dict = Depends(verify_admin)):
    """Download database backup"""
    import shutil
    try:
        # Create a temporary backup
        backup_path = f"{DATABASE_PATH}.backup"
        shutil.copy2(DATABASE_PATH, backup_path)
        
        # Return the backup file
        return FileResponse(
            path=backup_path,
            filename=f"database_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db",
            media_type="application/octet-stream"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Backup failed: {str(e)}")

@app.delete("/v2/admin/clear-reports")
async def clear_all_reports(token_data: dict = Depends(verify_admin)):
    """Clear all reports from database"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM reports")
        deleted_count = cursor.rowcount
        
        # Reset report counts for all users
        cursor.execute("UPDATE users SET reportCount = 0")
        
        conn.commit()
        conn.close()
        
        return {"message": f"Successfully cleared {deleted_count} reports", "deleted": deleted_count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear reports: {str(e)}")

@app.post("/v2/admin/reset-system")
async def reset_system(token_data: dict = Depends(verify_admin)):
    """Reset entire system - DANGEROUS!"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Delete all reports
        cursor.execute("DELETE FROM reports")
        
        # Delete all users except owner
        cursor.execute("DELETE FROM users WHERE isProtected = 0")
        
        # Delete all credentials
        cursor.execute("DELETE FROM credentials")
        
        # Reset settings to defaults
        cursor.execute("DELETE FROM settings")
        cursor.execute("""
            INSERT INTO settings (key, value, updated_at) VALUES 
            ('maintenanceMode', 'false', ?),
            ('registrationEnabled', 'true', ?),
            ('requireApproval', 'false', ?)
        """, (
            datetime.now(timezone.utc).isoformat(),
            datetime.now(timezone.utc).isoformat(),
            datetime.now(timezone.utc).isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        return {"message": "System reset successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"System reset failed: {str(e)}")

@app.post("/v2/admin/clear-cache")
async def clear_cache(token_data: dict = Depends(verify_admin)):
    """Clear application cache"""
    # Since we don't have a cache system yet, just return success
    return {"message": "Cache cleared successfully"}

@app.post("/v2/admin/optimize-db")
async def optimize_database(token_data: dict = Depends(verify_admin)):
    """Optimize database performance"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Run VACUUM to rebuild the database file
        cursor.execute("VACUUM")
        
        # Analyze tables for query optimization
        cursor.execute("ANALYZE")
        
        conn.commit()
        conn.close()
        
        return {"message": "Database optimized successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Optimization failed: {str(e)}")

# Frontend Routes - Serve HTML pages
@app.get("/")
async def root():
    """Redirect root to login page"""
    return RedirectResponse(url="/login.html")

@app.get("/login.html", response_class=HTMLResponse)
async def login_page():
    """Serve login page"""
    return FileResponse(os.path.join(FRONTEND_DIR, "login.html"))

@app.get("/register.html", response_class=HTMLResponse)
async def register_page():
    """Serve register page"""
    return FileResponse(os.path.join(FRONTEND_DIR, "register.html"))

@app.get("/dashboard.html", response_class=HTMLResponse)
async def dashboard_page():
    """Serve dashboard page"""
    return FileResponse(os.path.join(FRONTEND_DIR, "dashboard.html"))

@app.get("/reporting.html", response_class=HTMLResponse)
async def reporting_page():
    """Serve reporting page"""
    return FileResponse(os.path.join(FRONTEND_DIR, "reporting.html"))

@app.get("/history.html", response_class=HTMLResponse)
async def history_page():
    """Serve history page"""
    return FileResponse(os.path.join(FRONTEND_DIR, "history.html"))

@app.get("/settings.html", response_class=HTMLResponse)
async def settings_page():
    """Serve settings page"""
    return FileResponse(os.path.join(FRONTEND_DIR, "settings.html"))

@app.get("/about.html", response_class=HTMLResponse)
async def about_page():
    """Serve about page"""
    return FileResponse(os.path.join(FRONTEND_DIR, "about.html"))

@app.get("/tos.html", response_class=HTMLResponse)
async def tos_page():
    """Serve Terms of Service page"""
    # TOS is always accessible, even in maintenance mode
    return FileResponse(os.path.join(FRONTEND_DIR, "tos.html"))

@app.get("/admin.html", response_class=HTMLResponse)
async def admin_page():
    """Serve admin page (bypasses maintenance for admins)"""
    return FileResponse(os.path.join(FRONTEND_DIR, "admin.html"))

# Run Server
if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting SWATNFO Backend...")
    uvicorn.run(app, host="0.0.0.0", port=8000)


