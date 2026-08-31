import sqlite3
from datetime import datetime, timedelta

DB_FILE = "wake_up.db"


def get_conn():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS wake_up (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL UNIQUE,
            status TEXT NOT NULL,
            time TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sleep (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL UNIQUE,
            status TEXT NOT NULL,
            time TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def save_sleep(date_str: str, status: str, time_str: str):
    conn = get_conn()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO sleep (date, status, time) VALUES (?, ?, ?)",
            (date_str, status, time_str),
        )
        conn.commit()
    finally:
        conn.close()


def get_today_sleep(date_str: str):
    conn = get_conn()
    row = conn.execute(
        "SELECT status FROM sleep WHERE date = ?", (date_str,)
    ).fetchone()
    conn.close()
    return row["status"] if row else None


def save_response(date_str: str, status: str, time_str: str):
    conn = get_conn()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO wake_up (date, status, time) VALUES (?, ?, ?)",
            (date_str, status, time_str),
        )
        conn.commit()
    finally:
        conn.close()


def get_history(days: int = 7):
    conn = get_conn()
    rows = conn.execute(
        "SELECT date, status, time FROM wake_up ORDER BY date DESC LIMIT ?",
        (days,),
    ).fetchall()
    conn.close()
    return rows


def get_stats():
    conn = get_conn()
    total = conn.execute("SELECT COUNT(*) as c FROM wake_up").fetchone()["c"]
    wins = conn.execute(
        "SELECT COUNT(*) as c FROM wake_up WHERE status = 'bangun'"
    ).fetchone()["c"]
    losses = conn.execute(
        "SELECT COUNT(*) as c FROM wake_up WHERE status = 'tidak_bangun'"
    ).fetchone()["c"]

    # Current streak
    rows = conn.execute(
        "SELECT date, status FROM wake_up ORDER BY date DESC"
    ).fetchall()
    conn.close()

    streak = 0
    for row in rows:
        if row["status"] == "bangun":
            streak += 1
        else:
            break

    return {
        "total": total,
        "wins": wins,
        "losses": losses,
        "streak": streak,
    }


def get_today_status(date_str: str):
    conn = get_conn()
    row = conn.execute(
        "SELECT status FROM wake_up WHERE date = ?", (date_str,)
    ).fetchone()
    conn.close()
    return row["status"] if row else None
