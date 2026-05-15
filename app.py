#!/usr/bin/env python3
"""
RESUME OPTIMIZER PRO – FAST START + FULL FEATURES
- Instantly starts (no waiting for APIs)
- Background job fetcher (real jobs from Himalayas + JSearch)
- Open ATS XML feeds (Personio, Lever)
- Automated expiry + deduplication
- Adzuna‑like country/location display
"""

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, Response, send_file
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_mail import Mail, Message
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_dance.contrib.google import make_google_blueprint, google
from flask_socketio import SocketIO, emit
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
import sqlite3
import hashlib
import secrets
import re
import requests
import time
import random
import feedparser
import csv
import qrcode
import pyotp
import io
import base64
import os
from io import StringIO, BytesIO
from PIL import Image
from werkzeug.utils import secure_filename
from functools import wraps
import json
import threading
from urllib.parse import quote
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import DBSCAN

# -------------------- APP CONFIG --------------------
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

# File upload
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'docx', 'txt'}
os.makedirs('static/avatars', exist_ok=True)
os.makedirs('uploads', exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Email (configure for production)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'your-email@gmail.com'
app.config['MAIL_PASSWORD'] = 'your-app-password'
app.config['MAIL_DEFAULT_SENDER'] = 'noreply@resumeoptimizer.com'
mail = Mail(app)

# Rate limiting (silence in‑memory warning)
limiter = Limiter(get_remote_address, default_limits=["200 per day", "50 per hour"])
limiter.init_app(app)
app.config['RATELIMIT_STORAGE_URL'] = 'memory://'

# Google OAuth (replace with your credentials)
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
google_bp = make_google_blueprint(
    client_id="YOUR_GOOGLE_CLIENT_ID",
    client_secret="YOUR_GOOGLE_CLIENT_SECRET",
    scope=["profile", "email"]
)
app.register_blueprint(google_bp, url_prefix="/login")

# Login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please login to access this page'

# SocketIO for real‑time notifications
socketio = SocketIO(app, cors_allowed_origins="*")

# Scheduler for daily alerts & expiry
scheduler = BackgroundScheduler()
scheduler.start()

# -------------------- API KEYS --------------------
# Get your free RapidAPI key from https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch
RAPIDAPI_KEY = "YOUR_RAPIDAPI_KEY_HERE"   # <-- REPLACE THIS

# -------------------- DATABASE --------------------
def get_db():
    conn = sqlite3.connect('resume_optimizer.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    # Users table (full version)
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            username TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            subscription TEXT DEFAULT 'free',
            subscription_end DATE,
            is_employer INTEGER DEFAULT 0,
            is_admin INTEGER DEFAULT 0,
            avatar TEXT DEFAULT 'default.png',
            totp_secret TEXT,
            totp_enabled INTEGER DEFAULT 0,
            email_notifications INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            bio TEXT,
            skills TEXT,
            experience_years INTEGER DEFAULT 0,
            linkedin_url TEXT,
            github_url TEXT,
            portfolio_url TEXT
        )
    ''')

    # Jobs table (with expiry and extra fields)
    c.execute('''
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            company TEXT NOT NULL,
            location TEXT,
            country TEXT,
            salary_min INTEGER,
            salary_max INTEGER,
            currency TEXT,
            job_type TEXT,
            experience_level TEXT,
            description TEXT,
            requirements TEXT,
            benefits TEXT,
            source TEXT,
            source_url TEXT,
            posted_date TIMESTAMP,
            is_remote INTEGER DEFAULT 0,
            is_featured INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            views_count INTEGER DEFAULT 0,
            applications_count INTEGER DEFAULT 0,
            industry TEXT,
            expiry_date TIMESTAMP
        )
    ''')

    # Applications, saved_jobs, alerts, searches (minimal for speed)
    c.execute('''
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            job_id TEXT,
            status TEXT DEFAULT 'applied',
            applied_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            notes TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS saved_jobs (
            user_id INTEGER,
            job_id TEXT,
            saved_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            notes TEXT,
            PRIMARY KEY (user_id, job_id)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS job_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            keyword TEXT,
            location TEXT,
            frequency TEXT,
            is_active INTEGER DEFAULT 1,
            created_date TIMESTAMP,
            last_sent TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS saved_searches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            keyword TEXT,
            location TEXT,
            job_type TEXT,
            is_remote INTEGER,
            created_date TIMESTAMP,
            last_notified TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS user_activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT,
            job_id TEXT,
            ip_address TEXT,
            created_date TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS testimonials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            content TEXT,
            rating INTEGER,
            is_approved INTEGER DEFAULT 0,
            created_date TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS company_reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT,
            user_id INTEGER,
            rating INTEGER,
            review TEXT,
            pros TEXT,
            cons TEXT,
            would_recommend INTEGER,
            employment_status TEXT,
            created_date TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS interview_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_title TEXT,
            category TEXT,
            question TEXT,
            sample_answer TEXT,
            tips TEXT,
            difficulty TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL,
            currency TEXT,
            plan_type TEXT,
            stripe_payment_id TEXT,
            status TEXT,
            created_date TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS user_skills (
            user_id INTEGER,
            skill_name TEXT,
            confidence REAL DEFAULT 1.0,
            updated_date TIMESTAMP,
            PRIMARY KEY (user_id, skill_name)
        )
    ''')
    # FTS5 full-text search
    try:
        c.execute('''
            CREATE VIRTUAL TABLE IF NOT EXISTS jobs_fts USING fts5(
                title, company, description, content=jobs
            )
        ''')
    except:
        pass

    # Sample interview questions
    c.execute("SELECT COUNT(*) FROM interview_questions")
    if c.fetchone()[0] == 0:
        questions = [
            ('Software Engineer', 'Technical', 'What is the difference between HTTP and HTTPS?',
             'HTTP is unencrypted while HTTPS uses SSL/TLS encryption.', 'Focus on security.', 'Medium'),
            ('Software Engineer', 'Behavioral', 'Tell me about a difficult decision you made.',
             'Use STAR method: Situation, Task, Action, Result.', 'Show leadership.', 'Medium'),
            ('Data Scientist', 'Technical', 'Explain supervised vs unsupervised learning.',
             'Supervised uses labeled data, unsupervised finds patterns.', 'Give examples.', 'Medium'),
        ]
        for q in questions:
            c.execute('INSERT INTO interview_questions (job_title, category, question, sample_answer, tips, difficulty) VALUES (?,?,?,?,?,?)', q)

    conn.commit()
    conn.close()

init_db()

# -------------------- USER MODEL --------------------
class User(UserMixin):
    def __init__(self, id, email, username, subscription, is_admin=0, totp_enabled=0):
        self.id = id
        self.email = email
        self.username = username
        self.subscription = subscription
        self.is_admin = is_admin
        self.totp_enabled = totp_enabled

@login_manager.user_loader
def load_user(user_id):
    conn = get_db()
    user = conn.execute("SELECT id, email, username, subscription, is_admin, totp_enabled FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    if user:
        return User(user['id'], user['email'], user['username'], user['subscription'], user['is_admin'], user['totp_enabled'])
    return None

# -------------------- HELPER FUNCTIONS --------------------
def clean_html(text):
    if not text:
        return ""
    cleaned = re.sub(r'<[^>]+>', '', text)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

def hash_password(password, salt=None):
    if not salt:
        salt = secrets.token_hex(32)
    h = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
    return salt, h.hex()

def verify_password(password, salt, hash_val):
    _, new = hash_password(password, salt)
    return new == hash_val

def send_email(recipient, subject, body):
    try:
        msg = Message(subject, recipients=[recipient], body=body)
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False

def send_welcome_email(email, username):
    subject = "Welcome to Resume Optimizer Pro!"
    body = f"Hi {username},\n\nStart your job search at http://localhost:5000/dashboard"
    send_email(email, subject, body)

# -------------------- FAST JOB FETCHERS (SHORT TIMEOUTS) --------------------
def fetch_himalayas_jobs(keyword, limit=30):
    """Free remote jobs – 5s timeout"""
    jobs = []
    try:
        url = "https://himalayas.app/jobs/api"
        params = {"search": keyword, "worldwide": "true", "limit": limit}
        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 200:
            data = response.json()
            for job in data.get('jobs', []):
                seniority = job.get('seniority')
                if isinstance(seniority, list):
                    seniority = ', '.join(seniority) if seniority else 'Not specified'
                elif not seniority:
                    seniority = 'Not specified'
                jobs.append({
                    'job_id': f"himalayas_{job.get('id')}",
                    'title': job.get('title', keyword)[:200],
                    'company': job.get('company', {}).get('name', 'Remote Company')[:100],
                    'location': 'Worldwide Remote',
                    'country': 'Remote',
                    'salary_min': job.get('salary', {}).get('min'),
                    'salary_max': job.get('salary', {}).get('max'),
                    'currency': job.get('salary', {}).get('currency', 'USD'),
                    'job_type': 'Remote',
                    'experience_level': seniority[:100],
                    'description': job.get('description', '')[:2000],
                    'requirements': '',
                    'benefits': '',
                    'source': 'Himalayas',
                    'source_url': job.get('url', '#'),
                    'posted_date': job.get('posted_at', datetime.now().isoformat()),
                    'is_remote': 1,
                    'industry': 'Technology'
                })
            print(f"✅ Himalayas: {len(jobs)} jobs")
        else:
            print(f"Himalayas status: {response.status_code}")
    except Exception as e:
        print(f"Himalayas timeout/skip: {e}")
    return jobs

def fetch_jsearch_jobs(keyword, location, limit=30):
    if RAPIDAPI_KEY == "YOUR_RAPIDAPI_KEY_HERE":
        return []
    jobs = []
    try:
        url = "https://jsearch.p.rapidapi.com/search"
        headers = {"X-RapidAPI-Key": RAPIDAPI_KEY, "X-RapidAPI-Host": "jsearch.p.rapidapi.com"}
        params = {"query": f"{keyword} in {location}", "page": "1", "num_pages": "1", "date_posted": "week", "results_wanted": str(limit)}
        response = requests.get(url, headers=headers, params=params, timeout=5)
        if response.status_code == 200:
            data = response.json()
            for job in data.get("data", []):
                jobs.append({
                    'job_id': f"jsearch_{job.get('job_id', hash(job.get('job_apply_link')))}",
                    'title': job.get('job_title', keyword)[:200],
                    'company': job.get('employer_name', 'Company')[:100],
                    'location': job.get('job_city', location),
                    'country': job.get('job_country', location),
                    'salary_min': job.get('job_min_salary'),
                    'salary_max': job.get('job_max_salary'),
                    'currency': job.get('job_salary_currency', 'USD'),
                    'job_type': job.get('job_employment_type', 'Full-time'),
                    'experience_level': 'Not specified',
                    'description': clean_html(job.get('job_description', ''))[:2000],
                    'requirements': '',
                    'benefits': '',
                    'source': 'JSearch',
                    'source_url': job.get('job_apply_link', '#'),
                    'posted_date': job.get('job_posted_at_datetime_utc', datetime.now().isoformat()),
                    'is_remote': 1 if job.get('job_is_remote', False) else 0,
                    'industry': job.get('employer_industry', 'Various')
                })
            print(f"✅ JSearch: {len(jobs)} jobs")
        else:
            print(f"JSearch status: {response.status_code}")
    except Exception as e:
        print(f"JSearch timeout/skip: {e}")
    return jobs[:limit]

def fetch_personio_jobs(company_name, limit=20):
    """Open ATS XML feed for Personio – works if company provides public XML"""
    jobs = []
    try:
        url = f"https://{company_name}.jobs.personio.de/xml"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            feed = feedparser.parse(response.text)
            for entry in feed.entries[:limit]:
                jobs.append({
                    'job_id': f"personio_{company_name}_{hash(entry.link)}",
                    'title': entry.get('title', 'Job Title')[:200],
                    'company': company_name.title(),
                    'location': entry.get('office', 'Unknown'),
                    'country': 'Germany',
                    'salary_min': None,
                    'salary_max': None,
                    'currency': 'EUR',
                    'job_type': entry.get('employment_type', 'Full-time'),
                    'experience_level': entry.get('experience', 'Not specified'),
                    'description': clean_html(entry.get('description', ''))[:2000],
                    'requirements': '',
                    'benefits': '',
                    'source': 'Personio',
                    'source_url': entry.get('link', '#'),
                    'posted_date': entry.get('published', datetime.now().isoformat()),
                    'is_remote': 1 if 'remote' in entry.get('office', '').lower() else 0,
                    'industry': 'Various'
                })
            print(f"✅ Personio ({company_name}): {len(jobs)} jobs")
        else:
            print(f"Personio {company_name} status: {response.status_code}")
    except Exception as e:
        print(f"Personio {company_name} error: {e}")
    return jobs

def fetch_lever_jobs(company_name, limit=20):
    """Open ATS API for Lever – free, no key"""
    jobs = []
    try:
        url = f"https://jobs.lever.co/{company_name}/postings"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            for job in data[:limit]:
                jobs.append({
                    'job_id': f"lever_{company_name}_{job.get('id')}",
                    'title': job.get('text', 'Job Title')[:200],
                    'company': company_name.title(),
                    'location': job.get('categories', {}).get('location', 'Remote'),
                    'country': job.get('countryCode', 'USA'),
                    'salary_min': None,
                    'salary_max': None,
                    'currency': 'USD',
                    'job_type': job.get('categories', {}).get('commitment', 'Full-time'),
                    'experience_level': job.get('categories', {}).get('level', 'Not specified'),
                    'description': clean_html(job.get('descriptionHtml', ''))[:2000],
                    'requirements': '',
                    'benefits': '',
                    'source': 'Lever',
                    'source_url': f"https://jobs.lever.co/{company_name}/{job.get('id')}",
                    'posted_date': job.get('createdAt', datetime.now().isoformat()),
                    'is_remote': 1 if 'remote' in job.get('categories', {}).get('location', '').lower() else 0,
                    'industry': 'Various'
                })
            print(f"✅ Lever ({company_name}): {len(jobs)} jobs")
        else:
            print(f"Lever {company_name} status: {response.status_code}")
    except Exception as e:
        print(f"Lever {company_name} error: {e}")
    return jobs

# -------------------- STATIC FALLBACK JOBS (ALWAYS AVAILABLE) --------------------
STATIC_JOBS = [
    {"job_id": "static_001", "title": "Senior Software Engineer", "company": "Google", "location": "Mountain View, CA", "country": "USA", "salary_min": 150000, "salary_max": 200000, "currency": "USD", "job_type": "Full-time", "description": "Build the future of search and AI.", "source": "Demo", "source_url": "https://careers.google.com", "posted_date": datetime.now().isoformat(), "is_remote": 0},
    {"job_id": "static_002", "title": "Data Scientist", "company": "Microsoft", "location": "Redmond, WA", "country": "USA", "salary_min": 130000, "salary_max": 180000, "currency": "USD", "job_type": "Full-time", "description": "Work on Azure AI and machine learning.", "source": "Demo", "source_url": "https://careers.microsoft.com", "posted_date": datetime.now().isoformat(), "is_remote": 1},
    {"job_id": "static_003", "title": "Frontend Developer", "company": "Safaricom", "location": "Nairobi", "country": "Kenya", "salary_min": 800000, "salary_max": 1200000, "currency": "KES", "job_type": "Full-time", "description": "Build mobile-first web apps for M-Pesa.", "source": "Demo", "source_url": "https://www.safaricom.co.ke/careers", "posted_date": datetime.now().isoformat(), "is_remote": 0},
    {"job_id": "static_004", "title": "Nurse", "company": "Aga Khan Hospital", "location": "Nairobi", "country": "Kenya", "salary_min": 600000, "salary_max": 900000, "currency": "KES", "job_type": "Full-time", "description": "Join a world-class healthcare team.", "source": "Demo", "source_url": "#", "posted_date": datetime.now().isoformat(), "is_remote": 0},
    {"job_id": "static_005", "title": "Accountant", "company": "KPMG", "location": "Nairobi", "country": "Kenya", "salary_min": 700000, "salary_max": 1100000, "currency": "KES", "job_type": "Full-time", "description": "Auditing and financial advisory services.", "source": "Demo", "source_url": "#", "posted_date": datetime.now().isoformat(), "is_remote": 0},
]

# -------------------- JOB AGGREGATION + DEDUPLICATION --------------------
def scrape_quick_jobs(keyword='software engineer', location='Remote', limit=50):
    """Fetch from working sources (short timeouts) + static fallback"""
    all_jobs = []
    # Himalayas (free, fast)
    all_jobs.extend(fetch_himalayas_jobs(keyword, limit//3))
    # JSearch (if key provided)
    if RAPIDAPI_KEY != "YOUR_RAPIDAPI_KEY_HERE":
        all_jobs.extend(fetch_jsearch_jobs(keyword, location, limit//3))
    # Open ATS examples (you can add more company names)
    for company in ["google", "microsoft", "safaricom"]:
        all_jobs.extend(fetch_lever_jobs(company, limit//10))
        all_jobs.extend(fetch_personio_jobs(company, limit//10))
    # If still empty, use static jobs
    if not all_jobs:
        all_jobs = STATIC_JOBS.copy()
    # Deduplicate by job_id (simple)
    seen = set()
    unique = []
    for job in all_jobs:
        if job['job_id'] not in seen:
            seen.add(job['job_id'])
            unique.append(job)
    return unique

def save_jobs_to_db(jobs):
    conn = get_db()
    c = conn.cursor()
    saved = 0
    expiry_days = 30
    for job in jobs:
        try:
            expiry = (datetime.now() + timedelta(days=expiry_days)).isoformat()
            c.execute('''
                INSERT OR REPLACE INTO jobs 
                (job_id, title, company, location, country, salary_min, salary_max, currency, job_type, experience_level,
                 description, requirements, benefits, source, source_url, posted_date, is_remote, is_active, industry, expiry_date)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ''', (
                job['job_id'], job['title'], job['company'], job['location'], job.get('country', 'Remote'),
                job.get('salary_min'), job.get('salary_max'), job.get('currency', 'USD'),
                job.get('job_type', 'Full-time'), job.get('experience_level', 'N/A'),
                job.get('description', '')[:2000], job.get('requirements', ''), job.get('benefits', ''),
                job.get('source', 'Unknown'), job.get('source_url', '#'), job.get('posted_date', datetime.now().isoformat()),
                job.get('is_remote', 0), 1, job.get('industry', 'Various'), expiry
            ))
            saved += 1
        except Exception as e:
            print(f"Save error for {job.get('job_id')}: {e}")
    conn.commit()
    conn.close()
    print(f"✅ Saved {saved} jobs")
    return saved

def initial_load():
    """Run once in background – fetches real jobs without blocking startup"""
    print("🚀 Background job fetch started...")
    jobs = scrape_quick_jobs(limit=100)
    if jobs:
        save_jobs_to_db(jobs)
        print(f"✅ Loaded {len(jobs)} jobs")
    else:
        print("⚠️ No jobs fetched – static fallback already in DB")
        save_jobs_to_db(STATIC_JOBS)

# -------------------- AUTOMATED EXPIRY (DAILY) --------------------
def auto_expiry_jobs():
    """Mark jobs as expired if older than 30 days"""
    conn = get_db()
    c = conn.cursor()
    cutoff = (datetime.now() - timedelta(days=30)).isoformat()
    c.execute("UPDATE jobs SET is_active = 0 WHERE posted_date < ? AND is_active = 1", (cutoff,))
    conn.commit()
    conn.close()
    print("✅ Expired jobs deactivated")

scheduler.add_job(auto_expiry_jobs, 'cron', hour=3)

# -------------------- DATABASE QUERIES --------------------
def get_all_jobs(filters=None, page=1, per_page=20):
    conn = get_db()
    c = conn.cursor()
    offset = (page - 1) * per_page
    query = "SELECT * FROM jobs WHERE is_active = 1"
    params = []
    if filters:
        if filters.get('keyword'):
            try:
                fts = c.execute("SELECT rowid FROM jobs_fts WHERE jobs_fts MATCH ? LIMIT 200", (filters['keyword'] + '*',)).fetchall()
                if fts:
                    rowids = ','.join(str(r[0]) for r in fts)
                    query += f" AND id IN ({rowids})"
                else:
                    query += " AND (title LIKE ? OR company LIKE ?)"
                    params.append(f"%{filters['keyword']}%")
                    params.append(f"%{filters['keyword']}%")
            except:
                query += " AND (title LIKE ? OR company LIKE ?)"
                params.append(f"%{filters['keyword']}%")
                params.append(f"%{filters['keyword']}%")
        if filters.get('country') and filters['country'] != 'All':
            query += " AND country = ?"
            params.append(filters['country'])
        if filters.get('job_type') and filters['job_type'] != 'All':
            query += " AND job_type = ?"
            params.append(filters['job_type'])
        if filters.get('is_remote') is not None:
            query += " AND is_remote = ?"
            params.append(filters['is_remote'])
    query += " ORDER BY posted_date DESC LIMIT ? OFFSET ?"
    params.extend([per_page, offset])
    jobs = c.execute(query, params).fetchall()
    total = c.execute("SELECT COUNT(*) FROM jobs WHERE is_active = 1").fetchone()[0]
    conn.close()
    return jobs, total

def get_job_by_id(job_id):
    conn = get_db()
    job = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
    if not job:
        try:
            numeric = int(job_id)
            job = conn.execute("SELECT * FROM jobs WHERE id = ?", (numeric,)).fetchone()
        except:
            pass
    conn.close()
    return job

def get_company_jobs(company_name):
    conn = get_db()
    jobs = conn.execute("SELECT * FROM jobs WHERE company = ? AND is_active = 1 ORDER BY posted_date DESC", (company_name,)).fetchall()
    conn.close()
    return jobs

# -------------------- OTHER FEATURES (SALARY, ANALYZER, ETC.) --------------------
def calculate_salary(title, location, experience):
    base = 800000 if location == 'Kenya' else 80000 if location == 'USA' else 45000
    multiplier = 1 + (min(experience, 20) * 0.03)
    est = base * multiplier
    currency = 'KES' if location == 'Kenya' else 'USD'
    return {'min': int(est * 0.85), 'max': int(est * 1.15), 'average': int(est), 'currency': currency}

def analyze_resume(resume_text, job_desc):
    resume_low = resume_text.lower()
    job_low = job_desc.lower()
    words = re.findall(r'\b[a-z]{4,}\b', job_low)
    stop = {'this', 'that', 'with', 'from', 'have', 'will', 'your', 'their'}
    keywords = list(set([w for w in words if w not in stop and len(w) > 3]))
    matched = [k for k in keywords if k in resume_low]
    score = int((len(matched) / len(keywords)) * 100) if keywords else 0
    return {'score': score, 'matched': len(matched), 'total': len(keywords), 'missing': [k for k in keywords if k not in resume_low][:15]}

def log_activity(user_id, action, job_id=None, ip=None):
    conn = get_db()
    conn.execute("INSERT INTO user_activity_log (user_id, action, job_id, ip_address, created_date) VALUES (?,?,?,?,?)",
                 (user_id, action, job_id, ip or request.remote_addr, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Admin access required', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated

# -------------------- ROUTES (FULL SET – KEEPING ALL EXISTING) --------------------
@app.route('/')
def index():
    jobs, _ = get_all_jobs(page=1, per_page=6)
    all_jobs, _ = get_all_jobs()
    stats = {
        'total_jobs': len(all_jobs),
        'kenya_jobs': len([j for j in all_jobs if j['country'] == 'Kenya']),
        'remote_jobs': len([j for j in all_jobs if j['is_remote']]),
        'companies': len(set(j['company'] for j in all_jobs))
    }
    return render_template('index.html', featured_jobs=jobs, stats=stats)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        conn = get_db()
        user = conn.execute("SELECT id, username, password_hash, salt, subscription, is_admin, totp_enabled, totp_secret FROM users WHERE email = ?", (email,)).fetchone()
        conn.close()
        if user and verify_password(password, user['salt'], user['password_hash']):
            if user['totp_enabled']:
                session['pending_user_id'] = user['id']
                session['pending_totp_secret'] = user['totp_secret']
                return redirect(url_for('verify_2fa'))
            login_user(User(user['id'], email, user['username'], user['subscription'], user['is_admin'], user['totp_enabled']))
            log_activity(user['id'], 'login')
            flash('Logged in successfully!', 'success')
            return redirect(url_for('dashboard'))
        flash('Invalid email or password', 'error')
    return render_template('login.html')

@app.route('/verify-2fa', methods=['GET', 'POST'])
def verify_2fa():
    if 'pending_user_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        code = request.form.get('code')
        totp = pyotp.TOTP(session['pending_totp_secret'])
        if totp.verify(code):
            conn = get_db()
            user = conn.execute("SELECT id, email, username, subscription, is_admin FROM users WHERE id = ?", (session['pending_user_id'],)).fetchone()
            conn.close()
            login_user(User(user['id'], user['email'], user['username'], user['subscription'], user['is_admin'], 1))
            session.pop('pending_user_id', None)
            session.pop('pending_totp_secret', None)
            flash('2FA verified!', 'success')
            return redirect(url_for('dashboard'))
        flash('Invalid verification code', 'error')
    return render_template('verify_2fa.html')

@app.route('/setup-2fa', methods=['GET', 'POST'])
@login_required
def setup_2fa():
    if request.method == 'POST':
        code = request.form.get('code')
        if 'temp_totp_secret' not in session:
            return redirect(url_for('setup_2fa'))
        totp = pyotp.TOTP(session['temp_totp_secret'])
        if totp.verify(code):
            conn = get_db()
            conn.execute("UPDATE users SET totp_secret = ?, totp_enabled = 1 WHERE id = ?", (session['temp_totp_secret'], current_user.id))
            conn.commit()
            conn.close()
            session.pop('temp_totp_secret', None)
            flash('2FA enabled successfully!', 'success')
            return redirect(url_for('profile'))
        flash('Invalid verification code', 'error')
    secret = pyotp.random_base32()
    session['temp_totp_secret'] = secret
    totp = pyotp.TOTP(secret)
    provisioning_uri = totp.provisioning_uri(current_user.email, issuer_name="ResumeOptimizer")
    qr = qrcode.make(provisioning_uri)
    buffered = BytesIO()
    qr.save(buffered, format="PNG")
    qr_base64 = base64.b64encode(buffered.getvalue()).decode()
    return render_template('setup_2fa.html', qr_code=qr_base64, secret=secret)

@app.route('/disable-2fa', methods=['POST'])
@login_required
def disable_2fa():
    conn = get_db()
    conn.execute("UPDATE users SET totp_enabled = 0, totp_secret = NULL WHERE id = ?", (current_user.id,))
    conn.commit()
    conn.close()
    flash('2FA disabled', 'info')
    return redirect(url_for('profile'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        if len(password) < 8:
            flash('Password must be at least 8 characters', 'error')
            return redirect(url_for('register'))
        conn = get_db()
        if conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone():
            flash('Email already registered', 'error')
            conn.close()
            return redirect(url_for('register'))
        salt, phash = hash_password(password)
        conn.execute("INSERT INTO users (email, username, password_hash, salt, created_at) VALUES (?,?,?,?,?)", (email, username, phash, salt, datetime.now().isoformat()))
        conn.commit()
        conn.close()
        send_welcome_email(email, username)
        flash('Account created! Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    log_activity(current_user.id, 'logout')
    logout_user()
    flash('Logged out', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db()
    applications = conn.execute('''
        SELECT a.*, j.title, j.company, j.location FROM applications a JOIN jobs j ON a.job_id = j.job_id WHERE a.user_id = ? ORDER BY a.applied_date DESC
    ''', (current_user.id,)).fetchall()
    saved_jobs = conn.execute('''
        SELECT j.*, sj.notes FROM jobs j JOIN saved_jobs sj ON j.job_id = sj.job_id WHERE sj.user_id = ? ORDER BY sj.saved_date DESC
    ''', (current_user.id,)).fetchall()
    job_alerts = conn.execute("SELECT * FROM job_alerts WHERE user_id = ? ORDER BY created_date DESC", (current_user.id,)).fetchall()
    saved_searches = conn.execute("SELECT * FROM saved_searches WHERE user_id = ? ORDER BY created_date DESC", (current_user.id,)).fetchall()
    status_counts = {'applied':0, 'reviewing':0, 'interview':0, 'offer':0, 'rejected':0}
    for app in applications:
        if app['status'] in status_counts:
            status_counts[app['status']] += 1
    conn.close()
    return render_template('dashboard.html', username=current_user.username, applications=applications, saved_jobs=saved_jobs, job_alerts=job_alerts, saved_searches=saved_searches, status_counts=status_counts)

@app.route('/jobs')
def jobs():
    page = request.args.get('page', 1, type=int)
    keyword = request.args.get('search', '')
    country = request.args.get('country', 'All')
    job_type = request.args.get('job_type', 'All')
    is_remote = request.args.get('is_remote')
    filters = {'keyword': keyword, 'country': country, 'job_type': job_type}
    if is_remote == 'true':
        filters['is_remote'] = 1
    elif is_remote == 'false':
        filters['is_remote'] = 0
    jobs_list, total = get_all_jobs(filters, page, 20)
    total_pages = (total + 19) // 20
    kenya_jobs = [j for j in jobs_list if j['country'] == 'Kenya']
    other_jobs = [j for j in jobs_list if j['country'] != 'Kenya']
    return render_template('jobs.html', kenya_jobs=kenya_jobs, other_jobs=other_jobs, search=keyword, selected_country=country, selected_job_type=job_type, page=page, total_pages=total_pages, total_jobs=total)

@app.route('/job/<job_id>')
def job_detail(job_id):
    job = get_job_by_id(job_id)
    if not job:
        flash('Job not found', 'error')
        return redirect(url_for('jobs'))
    similar, _ = get_all_jobs({'keyword': job['title'].split()[0]}, 1, 5)
    company_jobs = get_company_jobs(job['company'])
    log_activity(current_user.id if current_user.is_authenticated else 0, 'view_job', job_id)
    return render_template('job_detail.html', job=job, similar_jobs=similar, company_jobs=company_jobs)

@app.route('/apply/<job_id>', methods=['POST'])
@login_required
def apply_job(job_id):
    conn = get_db()
    existing = conn.execute("SELECT id FROM applications WHERE user_id = ? AND job_id = ?", (current_user.id, job_id)).fetchone()
    if existing:
        flash('You have already applied to this job', 'warning')
        return redirect(url_for('job_detail', job_id=job_id))
    conn.execute("INSERT INTO applications (user_id, job_id, applied_date) VALUES (?,?,?)", (current_user.id, job_id, datetime.now().isoformat()))
    conn.execute("UPDATE jobs SET applications_count = applications_count + 1 WHERE job_id=?", (job_id,))
    conn.commit()
    conn.close()
    log_activity(current_user.id, 'apply_job', job_id)
    flash('Application submitted! Good luck!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/save/<job_id>', methods=['POST'])
@login_required
def save_job(job_id):
    notes = request.form.get('notes', '')
    conn = get_db()
    conn.execute("INSERT OR IGNORE INTO saved_jobs (user_id, job_id, saved_date, notes) VALUES (?,?,?,?)", (current_user.id, job_id, datetime.now().isoformat(), notes))
    conn.commit()
    conn.close()
    flash('Job saved!', 'success')
    return redirect(request.referrer or url_for('jobs'))

@app.route('/create-alert', methods=['POST'])
@login_required
def create_alert():
    keyword = request.form['keyword']
    location = request.form['location']
    frequency = request.form['frequency']
    conn = get_db()
    conn.execute("INSERT INTO job_alerts (user_id, keyword, location, frequency, created_date) VALUES (?,?,?,?,?)", (current_user.id, keyword, location, frequency, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    flash(f'Job alert created for "{keyword}"', 'success')
    return redirect(url_for('dashboard'))

@app.route('/delete-alert/<int:alert_id>', methods=['POST'])
@login_required
def delete_alert(alert_id):
    conn = get_db()
    conn.execute("DELETE FROM job_alerts WHERE id = ? AND user_id = ?", (alert_id, current_user.id))
    conn.commit()
    conn.close()
    flash('Alert deleted', 'info')
    return redirect(url_for('dashboard'))

@app.route('/save-search', methods=['POST'])
@login_required
def save_search():
    keyword = request.form.get('keyword', '')
    location = request.form.get('location', '')
    job_type = request.form.get('job_type', '')
    is_remote = 1 if request.form.get('is_remote') else 0
    conn = get_db()
    conn.execute("INSERT INTO saved_searches (user_id, keyword, location, job_type, is_remote, created_date) VALUES (?,?,?,?,?,?)", (current_user.id, keyword, location, job_type, is_remote, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    flash('Search saved!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/delete-search/<int:search_id>', methods=['POST'])
@login_required
def delete_search(search_id):
    conn = get_db()
    conn.execute("DELETE FROM saved_searches WHERE id = ? AND user_id = ?", (search_id, current_user.id))
    conn.commit()
    conn.close()
    flash('Saved search deleted', 'info')
    return redirect(url_for('dashboard'))

@app.route('/export-applications')
@login_required
def export_applications():
    conn = get_db()
    apps = conn.execute('''
        SELECT a.applied_date, j.title, j.company, j.location, j.salary_min, j.salary_max, j.currency, a.status
        FROM applications a JOIN jobs j ON a.job_id = j.job_id WHERE a.user_id = ? ORDER BY a.applied_date DESC
    ''', (current_user.id,)).fetchall()
    conn.close()
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Date Applied', 'Job Title', 'Company', 'Location', 'Salary Min', 'Salary Max', 'Currency', 'Status'])
    for app in apps:
        writer.writerow([app['applied_date'][:10], app['title'], app['company'], app['location'], app['salary_min'] or '', app['salary_max'] or '', app['currency'], app['status']])
    response = Response(output.getvalue(), mimetype='text/csv')
    response.headers['Content-Disposition'] = 'attachment; filename=applications.csv'
    return response

@app.route('/upload-avatar', methods=['POST'])
@login_required
def upload_avatar():
    if 'avatar' not in request.files:
        flash('No file selected', 'error')
        return redirect(url_for('profile'))
    file = request.files['avatar']
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('profile'))
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_filename = f"{timestamp}_{filename}"
        os.makedirs('static/avatars', exist_ok=True)
        filepath = os.path.join('static/avatars', unique_filename)
        file.save(filepath)
        conn = get_db()
        conn.execute("UPDATE users SET avatar = ? WHERE id = ?", (unique_filename, current_user.id))
        conn.commit()
        conn.close()
        flash('Profile picture updated!', 'success')
    else:
        flash('Invalid file type', 'error')
    return redirect(url_for('profile'))

@app.route('/analyzer')
def analyzer():
    return render_template('analyzer.html')

@app.route('/analyze', methods=['POST'])
@limiter.limit("10 per minute")
def analyze():
    resume = request.form.get('resume', '')
    job_desc = request.form.get('job_desc', '')
    if not resume or not job_desc:
        return jsonify({'error': 'Please provide both'})
    result = analyze_resume(resume, job_desc)
    return jsonify(result)

@app.route('/salary-calculator')
def salary_calculator():
    return render_template('salary_calculator.html')

@app.route('/calculate-salary', methods=['POST'])
def calculate_salary_api():
    data = request.get_json()
    result = calculate_salary(data.get('title', ''), data.get('location', 'Kenya'), int(data.get('experience', 0)))
    return jsonify(result)

@app.route('/interview-prep')
def interview_prep():
    conn = get_db()
    questions = conn.execute("SELECT * FROM interview_questions").fetchall()
    conn.close()
    return render_template('interview_prep.html', questions=questions)

@app.route('/saved-jobs')
@login_required
def saved_jobs_page():
    conn = get_db()
    jobs = conn.execute('''
        SELECT j.*, sj.notes, sj.saved_date FROM jobs j JOIN saved_jobs sj ON j.job_id = sj.job_id WHERE sj.user_id = ? ORDER BY sj.saved_date DESC
    ''', (current_user.id,)).fetchall()
    conn.close()
    return render_template('saved_jobs.html', saved_jobs=jobs)

@app.route('/applications')
@login_required
def applications_page():
    conn = get_db()
    apps = conn.execute('''
        SELECT a.*, j.title, j.company, j.location FROM applications a JOIN jobs j ON a.job_id = j.job_id WHERE a.user_id = ? ORDER BY a.applied_date DESC
    ''', (current_user.id,)).fetchall()
    conn.close()
    return render_template('applications.html', applications=apps)

@app.route('/update-application/<int:app_id>', methods=['POST'])
@login_required
def update_application(app_id):
    status = request.form.get('status')
    conn = get_db()
    job = conn.execute('''
        SELECT j.title FROM applications a JOIN jobs j ON a.job_id = j.job_id WHERE a.id = ?
    ''', (app_id,)).fetchone()
    conn.execute("UPDATE applications SET status = ? WHERE id = ? AND user_id = ?", (status, app_id, current_user.id))
    conn.commit()
    conn.close()
    if job:
        socketio.emit('application_status_update', {'job_title': job['title'], 'new_status': status}, room=str(current_user.id))
    flash('Application status updated', 'success')
    return redirect(url_for('applications_page'))

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    conn = get_db()
    if request.method == 'POST':
        if 'change_password' in request.form:
            old = request.form.get('old_password')
            new = request.form.get('new_password')
            confirm = request.form.get('confirm_password')
            if new != confirm:
                flash('New passwords do not match', 'error')
            elif len(new) < 8:
                flash('Password too short', 'error')
            else:
                user = conn.execute("SELECT password_hash, salt FROM users WHERE id = ?", (current_user.id,)).fetchone()
                if user and verify_password(old, user['salt'], user['password_hash']):
                    salt, phash = hash_password(new)
                    conn.execute("UPDATE users SET password_hash = ?, salt = ? WHERE id = ?", (phash, salt, current_user.id))
                    conn.commit()
                    flash('Password changed!', 'success')
                else:
                    flash('Current password incorrect', 'error')
        elif 'email_notifications' in request.form:
            enabled = 1 if request.form.get('email_notifications') == 'on' else 0
            conn.execute("UPDATE users SET email_notifications = ? WHERE id = ?", (enabled, current_user.id))
            conn.commit()
            flash('Notification settings updated', 'success')
        else:
            bio = request.form.get('bio', '')
            skills = request.form.get('skills', '')
            exp = int(request.form.get('experience_years', 0))
            linkedin = request.form.get('linkedin_url', '')
            github = request.form.get('github_url', '')
            portfolio = request.form.get('portfolio_url', '')
            conn.execute("UPDATE users SET bio=?, skills=?, experience_years=?, linkedin_url=?, github_url=?, portfolio_url=? WHERE id=?", (bio, skills, exp, linkedin, github, portfolio, current_user.id))
            conn.commit()
            flash('Profile updated!', 'success')
    user = conn.execute("SELECT * FROM users WHERE id=?", (current_user.id,)).fetchone()
    conn.close()
    return render_template('profile.html', user=user)

@app.route('/pricing')
def pricing():
    return render_template('pricing.html')

@app.route('/post-job', methods=['GET', 'POST'])
@login_required
def post_job():
    if request.method == 'POST':
        flash('Job posting requires payment. Please upgrade to Pro plan.', 'warning')
        return redirect(url_for('pricing'))
    return render_template('post_job.html')

@app.route('/add-testimonial', methods=['POST'])
@login_required
def add_testimonial_route():
    content = request.form.get('content')
    rating = int(request.form.get('rating', 5))
    if content:
        conn = get_db()
        conn.execute("INSERT INTO testimonials (user_id, content, rating, created_date) VALUES (?,?,?,?)", (current_user.id, content, rating, datetime.now().isoformat()))
        conn.commit()
        conn.close()
        flash('Thank you for your testimonial! It will appear after review.', 'success')
    else:
        flash('Please enter a testimonial', 'error')
    return redirect(url_for('dashboard'))

@app.route('/match-jobs')
@login_required
def match_jobs():
    conn = get_db()
    user_skills = [row[0] for row in conn.execute("SELECT skill_name FROM user_skills WHERE user_id = ?", (current_user.id,)).fetchall()]
    jobs_list, _ = get_all_jobs(page=1, per_page=100)
    scored = []
    for job in jobs_list:
        job_text = (job['title'] + ' ' + job['company'] + ' ' + job['description']).lower()
        match = sum(1 for skill in user_skills if skill in job_text)
        score = int((match / len(user_skills)) * 100) if user_skills else 0
        scored.append((score, job))
    scored.sort(key=lambda x: x[0], reverse=True)
    conn.close()
    return render_template('matched_jobs.html', jobs=scored[:20], user_skills=user_skills)

@app.route('/upload-resume', methods=['POST'])
@login_required
def upload_resume():
    if 'resume' not in request.files:
        flash('No file selected', 'error')
        return redirect(url_for('profile'))
    file = request.files['resume']
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('profile'))
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_filename = f"{timestamp}_{filename}"
        filepath = os.path.join('uploads', unique_filename)
        file.save(filepath)
        content = ""
        if filename.endswith('.txt'):
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        else:
            content = f"Uploaded file: {filename}\n(Full extraction requires text format)"
        common_skills = ['python', 'java', 'javascript', 'sql', 'aws', 'docker', 'react', 'angular', 'node.js', 'django', 'flask', 'machine learning', 'data analysis', 'project management', 'leadership', 'communication']
        found_skills = [skill for skill in common_skills if skill in content.lower()]
        conn = get_db()
        conn.execute("DELETE FROM user_skills WHERE user_id = ?", (current_user.id,))
        for skill in found_skills:
            conn.execute("INSERT INTO user_skills (user_id, skill_name, confidence, updated_date) VALUES (?,?,?,?)", (current_user.id, skill, 1.0, datetime.now().isoformat()))
        conn.commit()
        conn.close()
        flash(f'Resume analyzed! Found skills: {", ".join(found_skills) if found_skills else "none"}', 'success')
    else:
        flash('Invalid file type', 'error')
    return redirect(url_for('profile'))

@app.route('/submit-review', methods=['POST'])
@login_required
def submit_review():
    company_name = request.form.get('company_name')
    rating = int(request.form.get('rating'))
    review = request.form.get('review')
    pros = request.form.get('pros', '')
    cons = request.form.get('cons', '')
    recommend = 1 if request.form.get('would_recommend') else 0
    emp_status = request.form.get('employment_status')
    conn = get_db()
    conn.execute('''
        INSERT INTO company_reviews (company_name, user_id, rating, review, pros, cons, would_recommend, employment_status, created_date)
        VALUES (?,?,?,?,?,?,?,?,?)
    ''', (company_name, current_user.id, rating, review, pros, cons, recommend, emp_status, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    flash('Review submitted!', 'success')
    return redirect(request.referrer or url_for('jobs'))

# -------------------- ADMIN ROUTES --------------------
@app.route('/admin/users')
@login_required
@admin_required
def admin_users():
    conn = get_db()
    users = conn.execute("SELECT id, username, email, subscription, created_at, is_admin FROM users ORDER BY id").fetchall()
    conn.close()
    return render_template('admin_users.html', users=users)

@app.route('/admin/users/details')
@login_required
@admin_required
def admin_user_details():
    conn = get_db()
    users = conn.execute('''
        SELECT id, email, username, password_hash, salt, subscription, is_admin, is_employer,
               created_at, last_login, bio, skills, experience_years, linkedin_url, github_url
        FROM users ORDER BY id
    ''').fetchall()
    conn.close()
    return render_template('admin_user_details.html', users=users)

@app.route('/admin/reset-password/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def admin_reset_password(user_id):
    new_password = request.form.get('new_password')
    if not new_password or len(new_password) < 8:
        flash('Password must be at least 8 characters', 'error')
        return redirect(url_for('admin_users'))
    salt, phash = hash_password(new_password)
    conn = get_db()
    conn.execute("UPDATE users SET password_hash = ?, salt = ? WHERE id = ?", (phash, salt, user_id))
    conn.commit()
    conn.close()
    flash(f'Password reset for user ID {user_id}', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/activity-log')
@login_required
@admin_required
def admin_activity_log():
    conn = get_db()
    logs = conn.execute('''
        SELECT l.*, u.username FROM user_activity_log l JOIN users u ON l.user_id = u.id ORDER BY l.created_date DESC LIMIT 200
    ''').fetchall()
    conn.close()
    return render_template('admin_activity_log.html', logs=logs)

@app.route('/admin/testimonials')
@login_required
@admin_required
def admin_testimonials():
    conn = get_db()
    testimonials = conn.execute('''
        SELECT t.*, u.username FROM testimonials t JOIN users u ON t.user_id = u.id ORDER BY t.created_date DESC
    ''').fetchall()
    conn.close()
    return render_template('admin_testimonials.html', testimonials=testimonials)

@app.route('/admin/approve-testimonial/<int:testimonial_id>', methods=['POST'])
@login_required
@admin_required
def approve_testimonial(testimonial_id):
    conn = get_db()
    conn.execute("UPDATE testimonials SET is_approved = 1 WHERE id = ?", (testimonial_id,))
    conn.commit()
    conn.close()
    flash('Testimonial approved', 'success')
    return redirect(url_for('admin_testimonials'))

@app.route('/admin/delete-testimonial/<int:testimonial_id>', methods=['POST'])
@login_required
@admin_required
def delete_testimonial(testimonial_id):
    conn = get_db()
    conn.execute("DELETE FROM testimonials WHERE id = ?", (testimonial_id,))
    conn.commit()
    conn.close()
    flash('Testimonial deleted', 'info')
    return redirect(url_for('admin_testimonials'))

@app.route('/admin/refresh-bulk-jobs', methods=['POST'])
@login_required
@admin_required
def admin_refresh_bulk_jobs():
    def refresh():
        print("Manual bulk refresh started...")
        jobs = scrape_quick_jobs(limit=200)
        if jobs:
            save_jobs_to_db(jobs)
            print(f"Saved {len(jobs)} jobs")
        else:
            print("No jobs found")
    threading.Thread(target=refresh).start()
    flash('Bulk refresh started in background. Check console.', 'info')
    return redirect(url_for('admin_users'))

# -------------------- GOOGLE LOGIN --------------------
@app.route('/login/google')
def google_login():
    if not google.authorized:
        return redirect(url_for('google.login'))
    resp = google.get('/oauth2/v2/userinfo')
    if resp.ok:
        user_info = resp.json()
        email = user_info['email']
        name = user_info.get('name', email.split('@')[0])
        conn = get_db()
        user = conn.execute("SELECT id, username, subscription, is_admin FROM users WHERE email = ?", (email,)).fetchone()
        if not user:
            salt, phash = hash_password(secrets.token_urlsafe(16))
            conn.execute("INSERT INTO users (email, username, password_hash, salt, created_at) VALUES (?,?,?,?,?)", (email, name, phash, salt, datetime.now().isoformat()))
            conn.commit()
            user = conn.execute("SELECT id, username, subscription, is_admin FROM users WHERE email = ?", (email,)).fetchone()
        conn.close()
        login_user(User(user['id'], email, user['username'], user['subscription'], user['is_admin'], 0))
        flash(f'Logged in with Google! Welcome {user["username"]}', 'success')
        return redirect(url_for('dashboard'))
    flash('Google login failed', 'error')
    return redirect(url_for('login'))

# -------------------- PDF REPORT --------------------
@app.route('/generate-report')
@login_required
def generate_report():
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, "Resume Optimizer - Job Market Report")
    c.setFont("Helvetica", 12)
    c.drawString(50, height - 80, f"Generated for: {current_user.username}")
    c.drawString(50, height - 100, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    conn = get_db()
    total_jobs = conn.execute("SELECT COUNT(*) FROM jobs WHERE is_active = 1").fetchone()[0]
    kenya_jobs = conn.execute("SELECT COUNT(*) FROM jobs WHERE country = 'Kenya' AND is_active = 1").fetchone()[0]
    remote_jobs = conn.execute("SELECT COUNT(*) FROM jobs WHERE is_remote = 1 AND is_active = 1").fetchone()[0]
    conn.close()
    c.drawString(50, height - 140, f"Total Jobs: {total_jobs}")
    c.drawString(50, height - 160, f"Kenya Jobs: {kenya_jobs}")
    c.drawString(50, height - 180, f"Remote Jobs: {remote_jobs}")
    c.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name='job_market_report.pdf', mimetype='application/pdf')

# -------------------- STRIPE (MONETIZATION) --------------------
import stripe
@app.route('/create-checkout-session', methods=['POST'])
@login_required
def create_checkout_session():
    stripe.api_key = 'sk_test_...'  # REPLACE with your Stripe secret key
    plan = request.get_json().get('plan_type', 'monthly')
    amount = 999 if plan == 'monthly' else 9990
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {'name': f'Resume Optimizer Pro - {plan}'},
                    'unit_amount': amount,
                    'recurring': {'interval': 'month'} if 'monthly' in plan else None
                },
                'quantity': 1,
            }],
            mode='subscription' if 'monthly' in plan else 'payment',
            success_url=url_for('payment_success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=url_for('pricing', _external=True),
            customer_email=current_user.email
        )
        return jsonify({'id': session.id})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/payment-success')
@login_required
def payment_success():
    conn = get_db()
    conn.execute("UPDATE users SET subscription = 'premium', subscription_end = ? WHERE id = ?", ((datetime.now() + timedelta(days=30)).isoformat(), current_user.id))
    conn.commit()
    conn.close()
    flash('Payment successful! You now have premium access.', 'success')
    return redirect(url_for('dashboard'))

# -------------------- ERROR HANDLERS --------------------
@app.errorhandler(404)
def not_found(e):
    return render_template('index.html', error='Page not found'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('index.html', error='Server error, please try again later'), 500

# -------------------- RUN --------------------
if __name__ == '__main__':
    # Start background job fetch (does not block server)
    threading.Thread(target=initial_load, daemon=True).start()
    # Silence rate‑limiting warning (development only)
    app.config['RATELIMIT_STORAGE_URL'] = 'memory://'
    # Start the server
    socketio.run(app, debug=True, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)