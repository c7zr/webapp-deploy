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
import asyncio
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

# Instagram User Agents Pool - Updated November 2025 (Latest versions with iPhone focus)
INSTAGRAM_USER_AGENTS = [
    # iOS Instagram App User Agents (iPhone 15, 14, 13 Pro models - Most reliable for bypasses)
    "Instagram 320.0.0.37.98 (iPhone16,1; iOS 17_5_1; en_US; en; scale=3.00; 1179x2556; 540844007)",  # iPhone 15 Pro
    "Instagram 321.0.0.36.110 (iPhone16,2; iOS 17_5_1; en_US; en; scale=3.00; 1290x2796; 541123456)",  # iPhone 15 Pro Max
    "Instagram 319.0.0.31.101 (iPhone15,2; iOS 17_4_1; en_US; en; scale=3.00; 1179x2556; 539456789)",  # iPhone 14 Pro
    "Instagram 318.0.0.32.109 (iPhone15,3; iOS 17_4_1; en_US; en; scale=3.00; 1290x2796; 538789012)",  # iPhone 14 Pro Max
    "Instagram 320.1.0.30.111 (iPhone14,2; iOS 17_3_1; en_US; en; scale=3.00; 1170x2532; 540234567)",  # iPhone 13 Pro
    "Instagram 319.2.0.35.98 (iPhone14,3; iOS 17_3_1; en_US; en; scale=3.00; 1284x2778; 539890123)",  # iPhone 13 Pro Max
    "Instagram 318.1.0.29.102 (iPhone16,1; iOS 17_5; en_US; en; scale=3.00; 1179x2556; 538567890)",  # iPhone 15 Pro
    "Instagram 320.0.0.38.95 (iPhone15,2; iOS 17_4; en_US; en; scale=3.00; 1179x2556; 540901234)",  # iPhone 14 Pro
    "Instagram 317.0.0.33.113 (iPhone14,5; iOS 17_2_1; en_US; en; scale=3.00; 1170x2532; 537345678)",  # iPhone 13
    "Instagram 319.0.0.34.104 (iPhone15,3; iOS 17_4; en_US; en; scale=3.00; 1290x2796; 539123456)",  # iPhone 14 Pro Max
    "Instagram 316.0.0.31.105 (iPhone14,2; iOS 17_1_2; en_US; en; scale=3.00; 1170x2532; 536678901)",  # iPhone 13 Pro
    "Instagram 320.0.0.36.102 (iPhone16,2; iOS 17_5; en_US; en; scale=3.00; 1290x2796; 540456789)",  # iPhone 15 Pro Max
    "Instagram 318.0.0.30.106 (iPhone15,2; iOS 17_3; en_US; en; scale=3.00; 1179x2556; 538012345)",  # iPhone 14 Pro
    "Instagram 319.1.0.32.98 (iPhone14,3; iOS 17_2; en_US; en; scale=3.00; 1284x2778; 539567890)",  # iPhone 13 Pro Max
    "Instagram 317.0.0.35.99 (iPhone16,1; iOS 17_4_1; en_US; en; scale=3.00; 1179x2556; 537890123)",  # iPhone 15 Pro
    # Android Instagram App User Agents (Android 14 devices - Secondary for diversity)
    "Instagram 320.0.0.34.98 Android (34/14; 560dpi; 1440x3120; samsung; SM-S918B; dm1q; qcom; en_US; 540678901)",  # Galaxy S23 Ultra
    "Instagram 319.0.0.36.101 Android (34/14; 420dpi; 1080x2400; Google; Pixel 8 Pro; husky; google; en_US; 539234567)",  # Pixel 8 Pro
    "Instagram 318.0.0.33.105 Android (34/14; 480dpi; 1080x2400; OnePlus; CPH2581; OP594DL1; qcom; en_US; 538456789)",  # OnePlus 12
    "Instagram 320.1.0.31.102 Android (34/14; 560dpi; 1440x3200; samsung; SM-S921B; b0s; exynos2400; en_US; 540890123)",  # Galaxy S24
    "Instagram 317.0.0.32.108 Android (33/13; 420dpi; 1080x2340; Xiaomi; 23078PND5G; mondrian; qcom; en_US; 537567890)",  # Xiaomi 13
    "Instagram 319.0.0.35.103 Android (34/14; 480dpi; 1080x2400; Google; Pixel 8; shiba; google; en_US; 539901234)",  # Pixel 8
    "Instagram 316.0.0.30.109 Android (33/13; 560dpi; 1440x3088; samsung; SM-S908B; b0s; exynos2200; en_US; 536234567)",  # Galaxy S22 Ultra
    "Instagram 318.1.0.34.104 Android (34/14; 440dpi; 1080x2400; OnePlus; CPH2449; OP535DL1; qcom; en_US; 538678901)",  # OnePlus 11
    "Instagram 320.0.0.37.99 Android (34/14; 420dpi; 1080x2340; Xiaomi; 2311DRK48C; zijin; qcom; en_US; 540123456)",  # Xiaomi 14
    "Instagram 319.2.0.33.106 Android (33/13; 560dpi; 1440x3200; samsung; SM-S911B; dm1q; exynos2300; en_US; 539789012)"  # Galaxy S23
]

# Web Browser User Agents for scraping - Updated November 2025
WEB_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 11.0; Win64; x64; rv:131.0) Gecko/20100101 Firefox/131.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:132.0) Gecko/20100101 Firefox/132.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15"
]

def get_random_user_agent():
    """Return a random Instagram user agent from the pool"""
    return random.choice(INSTAGRAM_USER_AGENTS)

def get_random_web_user_agent():
    """Return a random web browser user agent"""
    return random.choice(WEB_USER_AGENTS)

def get_rotating_user_agent(index: int = None):
    """Get user agent with rotation to avoid detection - returns different UA each time"""
    if index is not None:
        return INSTAGRAM_USER_AGENTS[index % len(INSTAGRAM_USER_AGENTS)]
    return random.choice(INSTAGRAM_USER_AGENTS)

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
    
    # Scheduled reports table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scheduled_reports (
            id TEXT PRIMARY KEY,
            userId TEXT NOT NULL,
            username TEXT NOT NULL,
            targets TEXT NOT NULL,
            method TEXT NOT NULL,
            scheduleTime TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            createdAt TEXT NOT NULL,
            executedAt TEXT,
            FOREIGN KEY (userId) REFERENCES users (id)
        )
    ''')
    
    # IP Logs table for security tracking
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ip_logs (
            id TEXT PRIMARY KEY,
            userId TEXT,
            username TEXT NOT NULL,
            ipAddress TEXT NOT NULL,
            action TEXT NOT NULL,
            userAgent TEXT,
            timestamp TEXT NOT NULL,
            success INTEGER DEFAULT 1
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

# Scheduled Reports Worker
async def scheduled_reports_worker():
    """Background task that checks and executes scheduled reports every 30 seconds"""
    while True:
        try:
            await asyncio.sleep(30)  # Check every 30 seconds
            
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            
            # Auto-cancel reports stuck in 'executing' status for more than 20 minutes
            timeout_cutoff = (datetime.now(timezone.utc) - timedelta(minutes=20)).isoformat()
            c.execute("""
                SELECT id, username 
                FROM scheduled_reports 
                WHERE status = 'executing' AND scheduleTime <= ?
            """, (timeout_cutoff,))
            
            stuck_reports = c.fetchall()
            if stuck_reports:
                print(f"⏱️ Found {len(stuck_reports)} stuck executing report(s) - auto-canceling...")
                for stuck_id, stuck_username in stuck_reports:
                    c.execute("""
                        UPDATE scheduled_reports 
                        SET status = 'failed', executedAt = ? 
                        WHERE id = ?
                    """, (datetime.now(timezone.utc).isoformat(), stuck_id))
                    print(f"   ❌ Auto-canceled stuck report {stuck_id} for user {stuck_username}")
                conn.commit()
            
            # Get pending reports that are due
            now = datetime.now(timezone.utc).isoformat()
            c.execute("""
                SELECT id, userId, username, targets, method, scheduleTime 
                FROM scheduled_reports 
                WHERE status = 'pending' AND scheduleTime <= ?
            """, (now,))
            
            due_reports = c.fetchall()
            
            if due_reports:
                print(f"📅 Found {len(due_reports)} scheduled report(s) due for execution")
            
            for report in due_reports:
                report_id, user_id, username, targets_json, method, schedule_time = report
                
                try:
                    targets = json.loads(targets_json)
                    print(f"⏰ Executing scheduled report {report_id} for user {username}")
                    print(f"   Targets: {len(targets)}, Method: {method}")
                    
                    # Mark as executing
                    c.execute("""
                        UPDATE scheduled_reports 
                        SET status = 'executing' 
                        WHERE id = ?
                    """, (report_id,))
                    conn.commit()
                    
                    # Get user credentials
                    c.execute("SELECT sessionId, csrfToken FROM credentials WHERE userId = ?", (user_id,))
                    creds = c.fetchone()
                    
                    if not creds or not creds[0] or not creds[1]:
                        print(f"   ❌ No valid credentials found for user {username}")
                        c.execute("""
                            UPDATE scheduled_reports 
                            SET status = 'failed', executedAt = ? 
                            WHERE id = ?
                        """, (datetime.now(timezone.utc).isoformat(), report_id))
                        conn.commit()
                        continue
                    
                    session_id, csrf_token = creds
                    
                    # Check if user has premium for better success rate
                    c.execute("SELECT isPremium, premiumExpiresAt FROM users WHERE id = ?", (user_id,))
                    user_data = c.fetchone()
                    user_is_premium = False
                    if user_data and user_data[0]:
                        # Check if premium is active
                        if user_data[1]:
                            expiry = datetime.fromisoformat(user_data[1])
                            user_is_premium = expiry > datetime.now(timezone.utc)
                        else:
                            user_is_premium = True
                    
                    # Execute reports for each target
                    success_count = 0
                    failed_count = 0
                    
                    for target in targets:
                        try:
                            # Get target ID first
                            target_id = get_target_id(target, session_id, csrf_token)
                            
                            if not target_id:
                                failed_count += 1
                                print(f"   ❌ Failed to get ID for {target}")
                                continue
                            
                            # Send report using existing function
                            success = instagram_send_report(
                                target_id, session_id, csrf_token, method, use_random_ua=True, is_premium=user_is_premium
                            )
                            
                            if success:
                                success_count += 1
                                print(f"   ✅ Reported {target}")
                            else:
                                failed_count += 1
                                print(f"   ❌ Failed to report {target}")
                            
                            # Save to history (correct table name is 'reports')
                            c.execute("""
                                INSERT INTO reports 
                                (id, userId, username, target, method, status, timestamp, details)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            """, (
                                str(uuid.uuid4()),
                                user_id,
                                username,
                                target,
                                method,
                                'success' if success else 'failed',
                                datetime.now(timezone.utc).isoformat(),
                                json.dumps({"scheduled": True, "scheduleId": report_id})
                            ))
                            
                            # Small delay between targets
                            time.sleep(2)
                            
                        except Exception as e:
                            failed_count += 1
                            print(f"   ❌ Error reporting {target}: {str(e)}")
                    
                    # Mark as completed
                    final_status = 'completed' if success_count > 0 else 'failed'
                    c.execute("""
                        UPDATE scheduled_reports 
                        SET status = ?, executedAt = ? 
                        WHERE id = ?
                    """, (final_status, datetime.now(timezone.utc).isoformat(), report_id))
                    conn.commit()
                    
                    print(f"   ✅ Scheduled report {report_id} completed: {success_count} success, {failed_count} failed")
                    
                except Exception as e:
                    print(f"   ❌ Error executing scheduled report {report_id}: {str(e)}")
                    c.execute("""
                        UPDATE scheduled_reports 
                        SET status = 'failed', executedAt = ? 
                        WHERE id = ?
                    """, (datetime.now(timezone.utc).isoformat(), report_id))
                    conn.commit()
            
            conn.close()
            
        except asyncio.CancelledError:
            print("📅 Scheduled reports worker cancelled")
            raise
        except Exception as e:
            print(f"❌ Error in scheduled reports worker: {str(e)}")
            await asyncio.sleep(30)  # Wait before retrying

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
    
    # Start background scheduler task
    scheduler_task = asyncio.create_task(scheduled_reports_worker())
    print("✅ Scheduled reports worker started")
    
    yield
    
    # Cancel scheduler on shutdown
    scheduler_task.cancel()
    try:
        await scheduler_task
    except asyncio.CancelledError:
        print("✅ Scheduled reports worker stopped")

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

async def verify_owner(token_data: dict = Depends(verify_token)):
    if token_data["role"] != "owner":
        raise HTTPException(status_code=403, detail="Owner access required")
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
        
        # Log IP address for registration
        log_id = str(uuid.uuid4())
        user_agent = request.headers.get('user-agent', 'Unknown')
        cursor.execute(
            "INSERT INTO ip_logs (id, userId, username, ipAddress, action, userAgent, timestamp, success) VALUES (?, ?, ?, ?, 'register', ?, ?, 1)",
            (log_id, user_id, user.username, client_ip, user_agent, datetime.now(timezone.utc).isoformat())
        )
        
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
async def login(credentials: UserLogin, request: Request):
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
    
    # Log successful login IP
    log_id = str(uuid.uuid4())
    client_ip = request.client.host
    user_agent = request.headers.get('user-agent', 'Unknown')
    cursor.execute(
        "INSERT INTO ip_logs (id, userId, username, ipAddress, action, userAgent, timestamp, success) VALUES (?, ?, ?, ?, 'login', ?, ?, 1)",
        (log_id, user["id"], user["username"], client_ip, user_agent, datetime.now(timezone.utc).isoformat())
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
    
    # Check if user has active premium
    try:
        has_active_premium = is_premium_active(user)
        premium_expires_at = user["premiumExpiresAt"] if "premiumExpiresAt" in user.keys() else None
    except Exception as e:
        print(f"Error checking premium status: {e}")
        has_active_premium = False
        premium_expires_at = None
    
    return {
        "username": user["username"],
        "email": user["email"],
        "role": user["role"],
        "reportCount": user["reportCount"],
        "createdAt": user["createdAt"],
        "isPremium": has_active_premium,
        "premiumExpiresAt": premium_expires_at
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

# Helper function: Send single report (Enhanced with SWATNFO custom bypasses)
def instagram_send_report(target_id: str, sessionid: str, csrftoken: str, method: str = "spam", use_random_ua: bool = True, is_premium: bool = False) -> bool:
    """Send a single report to Instagram with SWATNFO custom bypasses, rotating user agents, and proxy support"""
    proxy = get_random_proxy()
    
    try:
        # Map method names to reason_id and additional data
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
        
        # Premium users get iPhone user agents for better bypass (60% chance)
        # Free users get random mix of iPhone/Android (30% chance iPhone)
        if use_random_ua:
            if is_premium and random.random() < 0.60:
                # Premium: Prioritize iPhone 15 Pro/14 Pro user agents (first 15 in list)
                user_agent = random.choice(INSTAGRAM_USER_AGENTS[:15])
            else:
                # Free or 40% of premium: Use full pool
                user_agent = get_random_user_agent()
        else:
            user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/110.0"
        
        # SWATNFO BYPASS #1: Dynamic timestamp-based request ID generation
        request_timestamp = str(int(time.time() * 1000))
        request_id = hashlib.md5(f"{sessionid}{request_timestamp}{target_id}".encode()).hexdigest()[:16]
        
        # SWATNFO BYPASS #2: Randomized delay before request (anti-pattern detection)
        if is_premium:
            time.sleep(random.uniform(0.1, 0.3))  # Premium: 100-300ms
        else:
            time.sleep(random.uniform(0.2, 0.5))  # Free: 200-500ms
        
        # SWATNFO BYPASS #3: Build comprehensive header set with fingerprint rotation
        headers = {
            "User-Agent": user_agent,
            "Host": "i.instagram.com",
            'cookie': f"sessionid={sessionid}; csrftoken={csrftoken}; rur=VLL",  # Added rur for routing
            "X-CSRFToken": csrftoken,
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Origin": "https://www.instagram.com",
            "Referer": f"https://www.instagram.com/{target_id}/",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
        }
        
        # SWATNFO BYPASS #4: Premium gets Instagram app-specific headers
        if is_premium:
            headers.update({
                "X-IG-App-ID": "936619743392459",
                "X-Instagram-AJAX": request_id,  # Dynamic AJAX ID
                "X-ASBD-ID": "129477",
                "X-IG-WWW-Claim": "0",
                "X-Instagram-GIS": hashlib.md5(f"{csrftoken}{target_id}".encode()).hexdigest()[:32],
            })
        
        # SWATNFO BYPASS #5: Enhanced data payload with additional context
        data_parts = [
            f'source_name=',
            f'reason_id={reason_id}',
            f'frx_context={extra_data}',
        ]
        
        # Premium bypass: Add extra telemetry data to mimic real app behavior
        if is_premium:
            data_parts.extend([
                f'container_module=profile',
                f'__a=1',
                f'__d=www',
                f'__req={request_id[:8]}',
                f'dpr=2',
            ])
        
        data = '&'.join(data_parts)
        
        # SWATNFO BYPASS #6: Multi-retry logic with exponential backoff
        max_retries = 3 if is_premium else 1
        base_delay = 0.5
        
        for attempt in range(max_retries):
            try:
                # SWATNFO BYPASS #7: Randomize request order (sometimes use GET before POST)
                if is_premium and random.random() < 0.3:
                    # 30% of time, make a GET request first to appear more human
                    try:
                        requests.get(
                            f"https://i.instagram.com/api/v1/users/{target_id}/info/",
                            headers={**headers, "Accept": "application/json"},
                            proxies=proxy,
                            timeout=5
                        )
                    except:
                        pass  # Ignore errors, this is just for fingerprint diversity
                
                r3 = requests.post(
                    f"https://i.instagram.com/users/{target_id}/flag/",
                    headers=headers,
                    data=data,
                    allow_redirects=False,
                    proxies=proxy,
                    timeout=15 if is_premium else 10
                )
                
                # SWATNFO BYPASS #8: Smart status code handling
                if r3.status_code == 429:
                    if is_premium and attempt < max_retries - 1:
                        # Premium: Exponential backoff + proxy rotation
                        delay = base_delay * (2 ** attempt) + random.uniform(0.1, 0.5)
                        time.sleep(delay)
                        proxy = get_random_proxy()
                        continue
                    print("[ERROR] Rate limited")
                    return False
                elif r3.status_code == 500:
                    print("[ERROR] Target not found")
                    return False
                elif r3.status_code in [200, 302]:
                    return True
                elif r3.status_code == 400:
                    # Sometimes 400 means success for Instagram
                    if is_premium and "feedback_required" not in r3.text.lower():
                        return True
                    return False
                else:
                    return True  # Treat unexpected codes as success
                    
            except requests.exceptions.Timeout:
                if is_premium and attempt < max_retries - 1:
                    time.sleep(base_delay * (2 ** attempt))
                    continue
                return False
            except requests.exceptions.TooManyRedirects:
                return True
            except requests.exceptions.ProxyError:
                if is_premium and attempt < max_retries - 1:
                    proxy = get_random_proxy()
                    time.sleep(0.3)
                    continue
                return False
            except Exception as e:
                if is_premium and attempt < max_retries - 1:
                    time.sleep(base_delay * (2 ** attempt))
                    continue
                print(f"   ❌ Error sending report: {str(e)}")
                return False
        
        return False
            
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
    
    # Send reports multiple times (1-20) with threading for better speed
    successful_reports = 0
    failed_reports = 0
    
    # Use threading for reports > 5 for better speed
    if report_count <= 5:
        # Sequential for small counts
        for i in range(report_count):
            print(f"   📤 Sending report {i+1}/{report_count}")
            success = instagram_send_report(target_id, cred["sessionId"], cred["csrfToken"], report.method, use_random_ua=True, is_premium=has_active_premium)
            
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
    else:
        # Use threading for 6-20 reports for faster execution
        print(f"   🚀 Using 3 parallel threads for faster reporting")
        
        def send_single_report_thread(report_num: int) -> dict:
            try:
                success = instagram_send_report(target_id, cred["sessionId"], cred["csrfToken"], report.method, use_random_ua=True, is_premium=has_active_premium)
                return {"num": report_num, "success": success}
            except Exception as e:
                return {"num": report_num, "success": False, "error": str(e)}
        
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {executor.submit(send_single_report_thread, i): i for i in range(1, report_count + 1)}
            
            for future in as_completed(futures):
                result = future.result()
                
                # Log each report
                report_id = str(uuid.uuid4())
                cursor.execute('''
                    INSERT INTO reports (id, userId, username, target, targetId, method, status, type, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (report_id, token_data["user_id"], token_data["username"], report.target, 
                      target_id, report.method, 
                      "success" if result["success"] else "failed", "single", 
                      datetime.now(timezone.utc).isoformat()))
                
                if result["success"]:
                    successful_reports += 1
                    cursor.execute("UPDATE users SET reportCount = reportCount + 1 WHERE id = ?", (token_data["user_id"],))
                else:
                    failed_reports += 1
                
                time.sleep(0.5)  # Small delay between threads
    
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
    """Send bulk Instagram reports with threading for faster execution"""
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
    
    # Check if user has active premium status
    has_active_premium = is_premium_active(user) if user else False
    
    # Check if bulk reporting is allowed (admin/owner OR users with active premium)
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
    print(f"   Using 4 concurrent threads for faster processing")
    
    results = {
        "total": len(targets),
        "successful": 0,
        "failed": 0,
        "blacklisted": 0,
        "details": []
    }
    
    # Thread worker function for processing each target
    def process_target(target_info):
        idx, target = target_info
        target = target.strip().replace("@", "")
        
        if not target:
            return None
        
        print(f"\n   [{idx}/{len(targets)}] Processing @{target}")
        
        # Thread-safe database connection
        target_conn = get_db()
        target_cursor = target_conn.cursor()
        
        try:
            # Check if target is blacklisted
            target_cursor.execute("SELECT * FROM blacklist WHERE username = ?", (target.lower(),))
            blacklisted = target_cursor.fetchone()
            
            if blacklisted:
                print(f"   ⛔ @{target} is blacklisted")
                target_cursor.execute("UPDATE blacklist SET blocked_attempts = blocked_attempts + 1 WHERE username = ?", (target.lower(),))
                target_conn.commit()
                target_conn.close()
                return {
                    "target": target,
                    "status": "blacklisted",
                    "message": "Target is blacklisted"
                }
            
            # Get target ID
            target_id = get_target_id(target, cred["sessionId"], cred["csrfToken"])
            
            if not target_id:
                print(f"   ❌ @{target} not found")
                
                # Log failed report
                report_id = str(uuid.uuid4())
                target_cursor.execute('''
                    INSERT INTO reports (id, userId, username, target, targetId, method, status, type, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (report_id, token_data["user_id"], token_data["username"], target, 
                      None, method, "failed", "bulk", datetime.now(timezone.utc).isoformat()))
                target_conn.commit()
                target_conn.close()
                return {
                    "target": target,
                    "status": "failed",
                    "message": "User not found or private"
                }
            
            # Send multiple reports for this target
            target_success = 0
            target_failed = 0
            
            for report_num in range(count):
                success = instagram_send_report(target_id, cred["sessionId"], cred["csrfToken"], method, use_random_ua=True, is_premium=has_active_premium)
                
                # Log report
                report_id = str(uuid.uuid4())
                target_cursor.execute('''
                    INSERT INTO reports (id, userId, username, target, targetId, method, status, type, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (report_id, token_data["user_id"], token_data["username"], target, 
                      target_id, method, "success" if success else "failed", "bulk", 
                      datetime.now(timezone.utc).isoformat()))
                
                if success:
                    target_cursor.execute("UPDATE users SET reportCount = reportCount + 1 WHERE id = ?", (token_data["user_id"],))
                    target_success += 1
                else:
                    target_failed += 1
                
                # Small delay between reports for same target
                if report_num < count - 1:
                    time.sleep(0.8)
            
            target_conn.commit()
            target_conn.close()
            
            if target_success > 0:
                print(f"   ✅ @{target} - {target_success}/{count} reports sent")
                return {
                    "target": target,
                    "status": "success",
                    "message": f"{target_success}/{count} reports sent successfully",
                    "successful": target_success,
                    "failed": target_failed
                }
            else:
                print(f"   ❌ @{target} - all reports failed")
                return {
                    "target": target,
                    "status": "failed",
                    "message": "All reports failed"
                }
                
        except Exception as e:
            print(f"   ❌ Error processing @{target}: {str(e)}")
            target_conn.close()
            return {
                "target": target,
                "status": "failed",
                "message": f"Error: {str(e)}"
            }
    
    # Use ThreadPoolExecutor for concurrent target processing
    max_workers = 4  # Process 4 targets concurrently
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Create target list with indices
        target_list = [(idx + 1, target) for idx, target in enumerate(targets)]
        
        # Submit all targets for processing
        futures = {executor.submit(process_target, target_info): target_info for target_info in target_list}
        
        # Process results as they complete
        for future in as_completed(futures):
            result = future.result()
            
            if result:
                results["details"].append(result)
                
                if result["status"] == "success":
                    results["successful"] += 1
                elif result["status"] == "blacklisted":
                    results["blacklisted"] += 1
                else:
                    results["failed"] += 1
    
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
    
    # Validate count (1-500 with auto proxy switching)
    count = min(max(count, 1), 500)
    
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
    print(f"   Using enhanced multi-threading with rotating user agents")
    
    # Get target ID
    target_id = get_target_id(target, cred["sessionId"], cred["csrfToken"])
    
    if not target_id:
        print(f"❌ Failed to get target ID for @{target}")
        conn.close()
        raise HTTPException(status_code=404, detail=f"Could not find user @{target}. User may be private, deleted, or credentials may be invalid.")
    
    # Worker function for threading with rotating user agents
    def send_single_mass_report(report_num: int) -> dict:
        """Send a single report (runs in thread) with rotating user agent"""
        try:
            # Use rotating user agent for each report to avoid detection
            # Premium users get enhanced bypasses and retries
            success = instagram_send_report(target_id, cred["sessionId"], cred["csrfToken"], method, use_random_ua=True, is_premium=has_active_premium)
            
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
            return {"report_num": report_num, "success": False, "error": str(e)}
    
    # Use ThreadPoolExecutor for parallel reporting with enhanced thread count
    # Premium users get 30 concurrent threads for maximum speed
    max_workers = 30 if user_role in ["admin", "owner"] else 25
    successful = 0
    failed = 0
    
    print(f"   🚀 Starting {max_workers} parallel threads with rotating user agents...")
    
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

# Scheduled Reports Routes
@app.post("/v2/reports/schedule")
async def schedule_report(schedule_data: dict, token_data: dict = Depends(verify_token)):
    """Schedule reports for future execution - Free: 3 max, Premium: 50 max"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Get user info
    cursor.execute("SELECT username, isPremium FROM users WHERE id = ?", (token_data["user_id"],))
    user = cursor.fetchone()
    
    if not user:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check premium status
    has_active_premium = is_premium_active(user)
    
    # Set limits based on premium status
    max_scheduled = 50 if has_active_premium else 3
    
    # Count current scheduled reports (pending only)
    cursor.execute(
        "SELECT COUNT(*) as count FROM scheduled_reports WHERE userId = ? AND status = 'pending'",
        (token_data["user_id"],)
    )
    current_scheduled = cursor.fetchone()["count"]
    
    if current_scheduled >= max_scheduled:
        conn.close()
        raise HTTPException(
            status_code=403,
            detail=f"{'Premium' if has_active_premium else 'Free'} users can only have {max_scheduled} scheduled reports at a time. Cancel some existing scheduled reports first."
        )
    
    # Validate input
    targets = schedule_data.get("targets", [])
    method = schedule_data.get("method")
    schedule_time = schedule_data.get("scheduleTime")
    
    if not targets or not method or not schedule_time:
        conn.close()
        raise HTTPException(status_code=400, detail="Missing required fields: targets, method, scheduleTime")
    
    if len(targets) > max_scheduled:
        conn.close()
        raise HTTPException(
            status_code=400,
            detail=f"Cannot schedule more than {max_scheduled} targets at once"
        )
    
    # Validate schedule time is in the future
    try:
        schedule_dt = datetime.fromisoformat(schedule_time.replace('Z', '+00:00'))
        if schedule_dt <= datetime.now(timezone.utc):
            conn.close()
            raise HTTPException(status_code=400, detail="Schedule time must be in the future")
    except ValueError:
        conn.close()
        raise HTTPException(status_code=400, detail="Invalid schedule time format")
    
    # Create scheduled report
    report_id = "sched_" + hashlib.md5(f"{token_data['user_id']}{schedule_time}".encode()).hexdigest()
    
    cursor.execute('''
        INSERT INTO scheduled_reports (id, userId, username, targets, method, scheduleTime, status, createdAt)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        report_id,
        token_data["user_id"],
        user["username"],
        json.dumps(targets),
        method,
        schedule_time,
        "pending",
        datetime.now(timezone.utc).isoformat()
    ))
    
    conn.commit()
    conn.close()
    
    return {
        "success": True,
        "message": f"Scheduled {len(targets)} report(s) for {schedule_dt.strftime('%Y-%m-%d %H:%M UTC')}",
        "scheduledId": report_id,
        "scheduleTime": schedule_time,
        "targetCount": len(targets),
        "currentScheduled": current_scheduled + 1,
        "maxScheduled": max_scheduled
    }

@app.get("/v2/reports/scheduled")
async def get_scheduled_reports(token_data: dict = Depends(verify_token)):
    """Get all scheduled reports for the current user"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM scheduled_reports 
        WHERE userId = ? 
        ORDER BY scheduleTime ASC
    ''', (token_data["user_id"],))
    
    scheduled = []
    for row in cursor.fetchall():
        scheduled.append({
            "id": row["id"],
            "targets": json.loads(row["targets"]),
            "method": row["method"],
            "scheduleTime": row["scheduleTime"],
            "status": row["status"],
            "createdAt": row["createdAt"],
            "executedAt": row["executedAt"]
        })
    
    # Get user's max limit
    cursor.execute("SELECT isPremium, premiumExpiresAt FROM users WHERE id = ?", (token_data["user_id"],))
    user = cursor.fetchone()
    has_active_premium = is_premium_active(user)
    max_scheduled = 50 if has_active_premium else 3
    
    pending_count = sum(1 for s in scheduled if s["status"] == "pending")
    
    conn.close()
    
    return {
        "scheduled": scheduled,
        "total": len(scheduled),
        "pending": pending_count,
        "maxScheduled": max_scheduled,
        "isPremium": has_active_premium
    }

@app.delete("/v2/reports/scheduled/{schedule_id}")
async def cancel_scheduled_report(schedule_id: str, token_data: dict = Depends(verify_token)):
    """Cancel a scheduled report"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Check if scheduled report exists and belongs to user
    cursor.execute(
        "SELECT * FROM scheduled_reports WHERE id = ? AND userId = ?",
        (schedule_id, token_data["user_id"])
    )
    scheduled = cursor.fetchone()
    
    if not scheduled:
        conn.close()
        raise HTTPException(status_code=404, detail="Scheduled report not found")
    
    if scheduled["status"] != "pending":
        conn.close()
        raise HTTPException(status_code=400, detail="Cannot cancel non-pending scheduled report")
    
    # Delete the scheduled report
    cursor.execute("DELETE FROM scheduled_reports WHERE id = ?", (schedule_id,))
    conn.commit()
    conn.close()
    
    return {"message": "Scheduled report cancelled successfully"}

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
    
    if "isPremium" in user_data:
        updates.append("isPremium = ?")
        params.append(1 if user_data["isPremium"] else 0)
        
        # If setting premium to true, set expiry to 1 year from now
        if user_data["isPremium"]:
            updates.append("premiumExpiresAt = ?")
            expiry_date = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()
            params.append(expiry_date)
        else:
            # If removing premium, clear expiry date
            updates.append("premiumExpiresAt = ?")
            params.append(None)
    
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
        "requireApproval": settings.get("requireApproval", "false") == "true",
        "logIpAddresses": settings.get("logIpAddresses", "true") == "true",
        "ipWhitelist": settings.get("ipWhitelist", ""),
        "maxLoginAttempts": int(settings.get("maxLoginAttempts", "5")),
        "sessionTimeout": int(settings.get("sessionTimeout", "86400")),
        "enableApiRateLimit": settings.get("enableApiRateLimit", "true") == "true",
        "siteName": settings.get("siteName", "SWATNFO"),
        "supportEmail": settings.get("supportEmail", "support@swatnfo.com"),
        "enableAnnouncements": settings.get("enableAnnouncements", "true") == "true",
        "defaultUserRole": settings.get("defaultUserRole", "user")
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

@app.get("/v2/admin/ip-logs")
async def get_ip_logs(limit: int = 100, offset: int = 0, username: str = None, token_data: dict = Depends(verify_owner)):
    """Get IP logs - owner only endpoint for security tracking"""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        if username:
            cursor.execute(
                "SELECT * FROM ip_logs WHERE username = ? ORDER BY timestamp DESC LIMIT ? OFFSET ?",
                (username, limit, offset)
            )
        else:
            cursor.execute(
                "SELECT * FROM ip_logs ORDER BY timestamp DESC LIMIT ? OFFSET ?",
                (limit, offset)
            )
        
        logs = [dict(row) for row in cursor.fetchall()]
        
        # Get total count
        if username:
            cursor.execute("SELECT COUNT(*) as total FROM ip_logs WHERE username = ?", (username,))
        else:
            cursor.execute("SELECT COUNT(*) as total FROM ip_logs")
        
        total = cursor.fetchone()["total"]
        
        conn.close()
        
        return {
            "logs": logs,
            "total": total,
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=f"Error fetching IP logs: {str(e)}")

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
    """Return beautiful maintenance page with unique asymmetric design"""
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
            
            :root {
                --purple-primary: #8a2be2;
                --purple-light: #9d4edd;
                --purple-dark: #6a1bb2;
                --bg-dark: #0a0a14;
                --bg-card: rgba(255, 255, 255, 0.02);
            }
            
            body {
                font-family: 'Segoe UI', 'Apple Color Emoji', 'Segoe UI Emoji', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #0a0a14 0%, #1a1a2e 50%, #16213e 100%);
                color: white;
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                overflow: hidden;
                position: relative;
            }
            
            /* Animated Background Particles */
            .particles {
                position: absolute;
                width: 100%;
                height: 100%;
                overflow: hidden;
                z-index: 0;
            }
            
            .particle {
                position: absolute;
                background: radial-gradient(circle, rgba(138, 43, 226, 0.6) 0%, transparent 70%);
                border-radius: 50%;
                animation: float 20s infinite;
            }
            
            .particle:nth-child(1) { width: 300px; height: 300px; top: 10%; left: 10%; animation-delay: 0s; }
            .particle:nth-child(2) { width: 200px; height: 200px; top: 60%; left: 70%; animation-delay: 5s; }
            .particle:nth-child(3) { width: 250px; height: 250px; top: 40%; left: 50%; animation-delay: 10s; }
            
            @keyframes float {
                0%, 100% { transform: translate(0, 0) scale(1); opacity: 0.3; }
                25% { transform: translate(50px, -50px) scale(1.1); opacity: 0.5; }
                50% { transform: translate(-30px, 30px) scale(0.9); opacity: 0.4; }
                75% { transform: translate(40px, 20px) scale(1.05); opacity: 0.45; }
            }
            
            /* Main Container - Asymmetric Layout */
            .maintenance-container {
                position: relative;
                z-index: 10;
                max-width: 1200px;
                width: 90%;
                display: grid;
                grid-template-columns: 1fr 1.2fr;
                gap: 2rem;
                padding: 2rem;
            }
            
            /* Left Section - Status Card */
            .status-card {
                background: var(--bg-card);
                border: 1px solid rgba(138, 43, 226, 0.3);
                border-radius: 32px;
                padding: 3rem 2.5rem;
                position: relative;
                overflow: hidden;
                backdrop-filter: blur(20px);
                box-shadow: 0 25px 50px rgba(138, 43, 226, 0.2);
                animation: cardSlideIn 0.8s cubic-bezier(0.34, 1.56, 0.64, 1);
            }
            
            @keyframes cardSlideIn {
                0% { opacity: 0; transform: translateX(-50px) scale(0.9); }
                100% { opacity: 1; transform: translateX(0) scale(1); }
            }
            
            .status-card::before {
                content: '';
                position: absolute;
                top: -50%;
                right: -50%;
                width: 200%;
                height: 200%;
                background: radial-gradient(circle, rgba(138, 43, 226, 0.1) 0%, transparent 50%);
                animation: rotateGlow 15s linear infinite;
            }
            
            @keyframes rotateGlow {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            
            .logo-container {
                position: relative;
                z-index: 1;
                text-align: center;
                margin-bottom: 2rem;
            }
            
            .logo {
                font-size: 100px;
                filter: drop-shadow(0 0 30px rgba(138, 43, 226, 0.6));
                animation: iconPulse 3s ease-in-out infinite;
            }
            
            @keyframes iconPulse {
                0%, 100% { transform: scale(1) rotate(0deg); }
                50% { transform: scale(1.15) rotate(5deg); }
            }
            
            .brand-name {
                position: relative;
                z-index: 1;
                font-size: 3rem;
                font-weight: 700;
                background: linear-gradient(135deg, #fff 0%, var(--purple-primary) 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
                margin-bottom: 0.5rem;
                animation: titleReveal 1s ease-out;
            }
            
            @keyframes titleReveal {
                0% { opacity: 0; transform: translateY(20px); }
                100% { opacity: 1; transform: translateY(0); }
            }
            
            .status-badge {
                position: relative;
                z-index: 1;
                display: inline-block;
                padding: 0.75rem 1.5rem;
                background: rgba(251, 191, 36, 0.2);
                border: 1px solid rgba(251, 191, 36, 0.4);
                border-radius: 50px;
                color: #fbbf24;
                font-weight: 600;
                font-size: 0.95rem;
                margin-bottom: 2rem;
                animation: badgePulse 2s ease-in-out infinite;
            }
            
            @keyframes badgePulse {
                0%, 100% { box-shadow: 0 0 20px rgba(251, 191, 36, 0.3); }
                50% { box-shadow: 0 0 40px rgba(251, 191, 36, 0.5); }
            }
            
            .spinner-container {
                position: relative;
                z-index: 1;
                margin: 2rem auto;
                width: 80px;
                height: 80px;
            }
            
            .spinner {
                width: 80px;
                height: 80px;
                border: 4px solid rgba(138, 43, 226, 0.2);
                border-top: 4px solid var(--purple-primary);
                border-radius: 50%;
                animation: spin 1s linear infinite;
            }
            
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            
            /* Right Section - Info Grid */
            .info-section {
                display: flex;
                flex-direction: column;
                gap: 1.5rem;
                animation: cardSlideIn 0.8s cubic-bezier(0.34, 1.56, 0.64, 1) 0.2s both;
            }
            
            .message-card {
                background: var(--bg-card);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 24px;
                padding: 2rem;
                position: relative;
                overflow: hidden;
                backdrop-filter: blur(20px);
            }
            
            .message-card::after {
                content: '';
                position: absolute;
                bottom: 0;
                left: 0;
                right: 0;
                height: 3px;
                background: linear-gradient(90deg, transparent, var(--purple-primary), transparent);
                opacity: 0.5;
            }
            
            .message-title {
                font-size: 1.8rem;
                font-weight: 600;
                margin-bottom: 1rem;
                color: #fff;
            }
            
            .message-text {
                font-size: 1.1rem;
                color: rgba(255, 255, 255, 0.7);
                line-height: 1.8;
                margin-bottom: 0;
            }
            
            /* Features Grid */
            .features-grid {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 1rem;
            }
            
            .feature-box {
                background: rgba(138, 43, 226, 0.1);
                border: 1px solid rgba(138, 43, 226, 0.3);
                border-radius: 16px;
                padding: 1.5rem;
                text-align: center;
                transition: all 0.3s ease;
                animation: featureAppear 0.6s ease both;
            }
            
            .feature-box:nth-child(1) { animation-delay: 0.4s; }
            .feature-box:nth-child(2) { animation-delay: 0.5s; }
            .feature-box:nth-child(3) { animation-delay: 0.6s; }
            .feature-box:nth-child(4) { animation-delay: 0.7s; }
            
            @keyframes featureAppear {
                0% { opacity: 0; transform: scale(0.8); }
                100% { opacity: 1; transform: scale(1); }
            }
            
            .feature-box:hover {
                transform: translateY(-5px);
                border-color: rgba(138, 43, 226, 0.6);
                box-shadow: 0 10px 30px rgba(138, 43, 226, 0.3);
            }
            
            .feature-icon {
                font-size: 2.5rem;
                margin-bottom: 0.75rem;
                filter: drop-shadow(0 0 10px rgba(138, 43, 226, 0.4));
            }
            
            .feature-label {
                font-size: 0.95rem;
                color: var(--purple-light);
                font-weight: 600;
            }
            
            /* ETA Card */
            .eta-card {
                background: linear-gradient(135deg, rgba(138, 43, 226, 0.15) 0%, rgba(157, 78, 221, 0.1) 100%);
                border: 1px solid rgba(138, 43, 226, 0.4);
                border-radius: 20px;
                padding: 1.5rem;
                text-align: center;
            }
            
            .eta-label {
                font-size: 0.9rem;
                color: rgba(255, 255, 255, 0.6);
                margin-bottom: 0.5rem;
                text-transform: uppercase;
                letter-spacing: 1px;
            }
            
            .eta-time {
                font-size: 2rem;
                font-weight: 700;
                background: linear-gradient(135deg, #fff 0%, var(--purple-light) 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            }
            
            /* Footer */
            .footer {
                position: relative;
                z-index: 1;
                grid-column: 1 / -1;
                text-align: center;
                margin-top: 2rem;
                padding-top: 2rem;
                border-top: 1px solid rgba(255, 255, 255, 0.1);
                color: rgba(255, 255, 255, 0.5);
                font-size: 0.9rem;
            }
            
            /* Responsive Design */
            @media (max-width: 968px) {
                .maintenance-container {
                    grid-template-columns: 1fr;
                    padding: 1rem;
                }
                
                .features-grid {
                    grid-template-columns: 1fr;
                }
                
                .brand-name {
                    font-size: 2.5rem;
                }
                
                .logo {
                    font-size: 80px;
                }
            }
        </style>
    </head>
    <body>
        <div class="particles">
            <div class="particle"></div>
            <div class="particle"></div>
            <div class="particle"></div>
        </div>
        
        <div class="maintenance-container">
            <!-- Left Section - Status -->
            <div class="status-card">
                <div class="logo-container">
                    <div class="logo">🔧</div>
                </div>
                <h1 class="brand-name">SWATNFO</h1>
                <div class="status-badge">⚠️ Under Maintenance</div>
                <div class="spinner-container">
                    <div class="spinner"></div>
                </div>
            </div>
            
            <!-- Right Section - Information -->
            <div class="info-section">
                <div class="message-card">
                    <h2 class="message-title">We're Making Things Better</h2>
                    <p class="message-text">
                        Our team is currently performing scheduled maintenance to bring you exciting new features, 
                        performance improvements, and security enhancements. We'll be back online shortly!
                    </p>
                </div>
                
                <div class="features-grid">
                    <div class="feature-box">
                        <div class="feature-icon">✨</div>
                        <div class="feature-label">New Features</div>
                    </div>
                    <div class="feature-box">
                        <div class="feature-icon">⚡</div>
                        <div class="feature-label">Performance</div>
                    </div>
                    <div class="feature-box">
                        <div class="feature-icon">🔒</div>
                        <div class="feature-label">Security</div>
                    </div>
                    <div class="feature-box">
                        <div class="feature-icon">🎨</div>
                        <div class="feature-label">UI Updates</div>
                    </div>
                </div>
                
                <div class="eta-card">
                    <div class="eta-label">Estimated Return</div>
                    <div class="eta-time">Coming Soon</div>
                </div>
            </div>
            
            <div class="footer">
                <strong>SWATNFO</strong> - Instagram Report Bot v2.8 | Thank you for your patience
            </div>
        </div>
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
        backup_path = f"{DB_PATH}.backup"
        shutil.copy2(DB_PATH, backup_path)
        
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


