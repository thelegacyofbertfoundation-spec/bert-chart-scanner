"""
Dr. Inker LABS - Database Module
Handles user data, scan history, energy tracking, and referrals.
"""
import sqlite3
import os
import json
from datetime import datetime, timedelta
from config import DATABASE_PATH, FREE_DAILY_SCANS, REFERRAL_BONUS_SCANS


def get_db():
    """Get database connection."""
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """Initialize database tables."""
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_premium INTEGER DEFAULT 0,
            premium_until TIMESTAMP,
            total_scans INTEGER DEFAULT 0,
            referral_code TEXT UNIQUE,
            referred_by INTEGER,
            bonus_scans INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS daily_energy (
            user_id INTEGER,
            date TEXT,
            scans_used INTEGER DEFAULT 0,
            bonus_used INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, date)
        );

        CREATE TABLE IF NOT EXISTS scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            token TEXT,
            ticker TEXT,
            trend TEXT,
            action TEXT,
            confidence INTEGER,
            risk_level TEXT,
            verdict TEXT,
            full_analysis TEXT,
            image_file_id TEXT,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        );

        CREATE TABLE IF NOT EXISTS referrals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            referrer_id INTEGER,
            referred_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            bonus_awarded INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            type TEXT,
            amount INTEGER,
            stars_paid INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    conn.close()


def get_or_create_user(user_id: int, username: str = None, first_name: str = None) -> dict:
    """Get existing user or create new one."""
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    if not user:
        import hashlib
        ref_code = hashlib.md5(str(user_id).encode()).hexdigest()[:8].upper()
        conn.execute(
            "INSERT INTO users (user_id, username, first_name, referral_code) VALUES (?, ?, ?, ?)",
            (user_id, username, first_name, ref_code)
        )
        conn.commit()
        user = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    result = dict(user)
    conn.close()
    return result


def get_energy_status(user_id: int) -> dict:
    """Get user's current energy/scan status."""
    conn = get_db()
    user = dict(conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone())
    today = datetime.utcnow().strftime("%Y-%m-%d")
    
    daily = conn.execute(
        "SELECT * FROM daily_energy WHERE user_id = ? AND date = ?", (user_id, today)
    ).fetchone()
    
    scans_used_today = daily["scans_used"] if daily else 0
    
    # Check premium status
    is_premium = user["is_premium"] and (
        not user["premium_until"] or 
        datetime.fromisoformat(user["premium_until"]) > datetime.utcnow()
    )
    
    if is_premium:
        remaining = 999  # Unlimited
    else:
        base_remaining = max(0, FREE_DAILY_SCANS - scans_used_today)
        bonus_remaining = user.get("bonus_scans", 0)
        remaining = base_remaining + bonus_remaining
    
    conn.close()
    return {
        "user_id": user_id,
        "is_premium": is_premium,
        "scans_used_today": scans_used_today,
        "free_remaining": max(0, FREE_DAILY_SCANS - scans_used_today) if not is_premium else 999,
        "bonus_scans": user.get("bonus_scans", 0),
        "total_remaining": remaining,
        "total_scans_ever": user["total_scans"]
    }


def use_scan(user_id: int) -> bool:
    """Consume one scan. Returns True if successful, False if no energy."""
    energy = get_energy_status(user_id)
    if energy["total_remaining"] <= 0:
        return False
    
    conn = get_db()
    today = datetime.utcnow().strftime("%Y-%m-%d")
    
    if energy["free_remaining"] > 0:
        # Use free daily scan
        conn.execute("""
            INSERT INTO daily_energy (user_id, date, scans_used)
            VALUES (?, ?, 1)
            ON CONFLICT(user_id, date) DO UPDATE SET scans_used = scans_used + 1
        """, (user_id, today))
    else:
        # Use bonus scans
        conn.execute(
            "UPDATE users SET bonus_scans = MAX(0, bonus_scans - 1) WHERE user_id = ?",
            (user_id,)
        )
    
    conn.execute(
        "UPDATE users SET total_scans = total_scans + 1 WHERE user_id = ?",
        (user_id,)
    )
    conn.commit()
    conn.close()
    return True


def add_bonus_scans(user_id: int, amount: int, stars_paid: int = 0):
    """Add bonus scans to user's account."""
    conn = get_db()
    conn.execute(
        "UPDATE users SET bonus_scans = bonus_scans + ? WHERE user_id = ?",
        (amount, user_id)
    )
    conn.execute(
        "INSERT INTO transactions (user_id, type, amount, stars_paid) VALUES (?, 'scan_refill', ?, ?)",
        (user_id, amount, stars_paid)
    )
    conn.commit()
    conn.close()


def set_premium(user_id: int, months: int = 1, stars_paid: int = 0):
    """Set user as premium."""
    conn = get_db()
    until = datetime.utcnow() + timedelta(days=30 * months)
    conn.execute(
        "UPDATE users SET is_premium = 1, premium_until = ? WHERE user_id = ?",
        (until.isoformat(), user_id)
    )
    conn.execute(
        "INSERT INTO transactions (user_id, type, amount, stars_paid) VALUES (?, 'premium', ?, ?)",
        (user_id, months, stars_paid)
    )
    conn.commit()
    conn.close()


def save_scan(user_id: int, analysis: dict, image_file_id: str = None):
    """Save a scan result to history."""
    conn = get_db()
    conn.execute("""
        INSERT INTO scans (user_id, token, ticker, trend, action, confidence, risk_level, verdict, full_analysis, image_file_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        analysis.get("token"),
        analysis.get("ticker"),
        analysis.get("trend"),
        analysis.get("action"),
        analysis.get("confidence"),
        analysis.get("risk_level"),
        analysis.get("verdict"),
        json.dumps(analysis),
        image_file_id
    ))
    conn.commit()
    conn.close()


def get_scan_history(user_id: int, limit: int = 20) -> list:
    """Get user's scan history."""
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM scans WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
        (user_id, limit)
    ).fetchall()
    result = [dict(r) for r in rows]
    conn.close()
    return result


def process_referral(referrer_code: str, new_user_id: int) -> bool:
    """Process a referral and award bonus scans."""
    conn = get_db()
    referrer = conn.execute(
        "SELECT user_id FROM users WHERE referral_code = ?", (referrer_code,)
    ).fetchone()
    
    if not referrer or referrer["user_id"] == new_user_id:
        conn.close()
        return False
    
    # Check if already referred
    existing = conn.execute(
        "SELECT id FROM referrals WHERE referred_id = ?", (new_user_id,)
    ).fetchone()
    if existing:
        conn.close()
        return False
    
    conn.execute(
        "INSERT INTO referrals (referrer_id, referred_id, bonus_awarded) VALUES (?, ?, ?)",
        (referrer["user_id"], new_user_id, REFERRAL_BONUS_SCANS)
    )
    conn.execute(
        "UPDATE users SET referred_by = ?, bonus_scans = bonus_scans + 3 WHERE user_id = ?",
        (referrer["user_id"], new_user_id)
    )
    conn.execute(
        "UPDATE users SET bonus_scans = bonus_scans + ? WHERE user_id = ?",
        (REFERRAL_BONUS_SCANS, referrer["user_id"])
    )
    conn.commit()
    conn.close()
    return True


def get_referral_count(user_id: int) -> int:
    """Get how many people a user has referred."""
    conn = get_db()
    count = conn.execute(
        "SELECT COUNT(*) as c FROM referrals WHERE referrer_id = ?", (user_id,)
    ).fetchone()["c"]
    conn.close()
    return count


def get_leaderboard(limit: int = 10) -> list:
    """Get top scanners leaderboard."""
    conn = get_db()
    rows = conn.execute("""
        SELECT user_id, username, first_name, total_scans
        FROM users ORDER BY total_scans DESC LIMIT ?
    """, (limit,)).fetchall()
    result = [dict(r) for r in rows]
    conn.close()
    return result
