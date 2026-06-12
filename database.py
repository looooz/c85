import sqlite3
import os
from datetime import datetime


DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reminders.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT DEFAULT '',
            reminder_type TEXT NOT NULL,
            trigger_time TEXT NOT NULL,
            advance_minutes INTEGER DEFAULT 0,
            enabled INTEGER DEFAULT 1,
            last_triggered TEXT,
            week_day INTEGER,
            month_day INTEGER,
            sound_type TEXT DEFAULT 'default',
            sound_file TEXT,
            volume INTEGER DEFAULT 80,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS countdowns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            duration_seconds INTEGER NOT NULL,
            remaining_seconds INTEGER NOT NULL,
            start_time TEXT NOT NULL,
            is_running INTEGER DEFAULT 1,
            triggered INTEGER DEFAULT 0
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS intervals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT DEFAULT '',
            interval_minutes INTEGER NOT NULL,
            start_time TEXT,
            end_time TEXT,
            enabled INTEGER DEFAULT 1,
            is_paused INTEGER DEFAULT 0,
            last_triggered TEXT,
            sound_type TEXT DEFAULT 'default',
            volume INTEGER DEFAULT 80,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT DEFAULT '',
            reminder_type TEXT NOT NULL,
            triggered_at TEXT NOT NULL,
            is_read INTEGER DEFAULT 0
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    defaults = {
        "hourly_chime_enabled": "0",
        "hourly_chime_start": "9",
        "hourly_chime_end": "21",
        "hourly_chime_sound": "chime",
        "focus_mode_enabled": "0",
        "focus_mode_start": "",
        "focus_mode_end": "",
        "whitelist_fullscreen": "1",
        "default_sound": "default",
        "default_volume": "80",
        "tts_enabled": "0",
        "theme": "dark",
    }
    for k, v in defaults.items():
        c.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v)
        )
    conn.commit()
    conn.close()


def get_setting(key, default=""):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = c.fetchone()
    conn.close()
    return row["value"] if row else default


def set_setting(key, value):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value))
    )
    conn.commit()
    conn.close()


def get_all_settings():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT key, value FROM settings")
    rows = c.fetchall()
    conn.close()
    return {row["key"]: row["value"] for row in rows}


def add_reminder(data: dict) -> int:
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        """INSERT INTO reminders
           (title, content, reminder_type, trigger_time, advance_minutes,
            enabled, week_day, month_day, sound_type, sound_file, volume)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            data["title"],
            data.get("content", ""),
            data["reminder_type"],
            data["trigger_time"],
            data.get("advance_minutes", 0),
            1 if data.get("enabled", True) else 0,
            data.get("week_day"),
            data.get("month_day"),
            data.get("sound_type", "default"),
            data.get("sound_file"),
            data.get("volume", 80),
        ),
    )
    rid = c.lastrowid
    conn.commit()
    conn.close()
    return rid


def update_reminder(rid: int, data: dict):
    conn = get_connection()
    c = conn.cursor()
    fields = []
    values = []
    for key in (
        "title", "content", "reminder_type", "trigger_time",
        "advance_minutes", "enabled", "week_day", "month_day",
        "sound_type", "sound_file", "volume",
    ):
        if key in data:
            fields.append(f"{key} = ?")
            if key == "enabled":
                values.append(1 if data[key] else 0)
            else:
                values.append(data[key])
    if fields:
        values.append(rid)
        c.execute(
            f"UPDATE reminders SET {', '.join(fields)} WHERE id = ?", values
        )
        conn.commit()
    conn.close()


def delete_reminder(rid: int):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM reminders WHERE id = ?", (rid,))
    conn.commit()
    conn.close()


def get_reminders(enabled_only=False):
    conn = get_connection()
    c = conn.cursor()
    if enabled_only:
        c.execute("SELECT * FROM reminders WHERE enabled = 1 ORDER BY trigger_time")
    else:
        c.execute("SELECT * FROM reminders ORDER BY trigger_time")
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_reminder_by_id(rid: int):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM reminders WHERE id = ?", (rid,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


def update_reminder_last_triggered(rid: int, triggered_time: str):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "UPDATE reminders SET last_triggered = ? WHERE id = ?",
        (triggered_time, rid),
    )
    conn.commit()
    conn.close()


def add_countdown(data: dict) -> int:
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        """INSERT INTO countdowns
           (title, duration_seconds, remaining_seconds, start_time, is_running, triggered)
           VALUES (?, ?, ?, ?, 1, 0)""",
        (
            data["title"],
            data["duration_seconds"],
            data["duration_seconds"],
            datetime.now().isoformat(),
        ),
    )
    cid = c.lastrowid
    conn.commit()
    conn.close()
    return cid


def get_countdowns(active_only=False):
    conn = get_connection()
    c = conn.cursor()
    if active_only:
        c.execute("SELECT * FROM countdowns WHERE triggered = 0 ORDER BY start_time")
    else:
        c.execute("SELECT * FROM countdowns ORDER BY start_time DESC")
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_countdown(cid: int, data: dict):
    conn = get_connection()
    c = conn.cursor()
    fields = []
    values = []
    for key in ("remaining_seconds", "is_running", "triggered"):
        if key in data:
            fields.append(f"{key} = ?")
            values.append(data[key])
    if fields:
        values.append(cid)
        c.execute(
            f"UPDATE countdowns SET {', '.join(fields)} WHERE id = ?", values
        )
        conn.commit()
    conn.close()


def delete_countdown(cid: int):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM countdowns WHERE id = ?", (cid,))
    conn.commit()
    conn.close()


def add_interval(data: dict) -> int:
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        """INSERT INTO intervals
           (title, content, interval_minutes, start_time, end_time,
            enabled, sound_type, volume)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            data["title"],
            data.get("content", ""),
            data["interval_minutes"],
            data.get("start_time"),
            data.get("end_time"),
            1 if data.get("enabled", True) else 0,
            data.get("sound_type", "default"),
            data.get("volume", 80),
        ),
    )
    iid = c.lastrowid
    conn.commit()
    conn.close()
    return iid


def get_intervals(enabled_only=False):
    conn = get_connection()
    c = conn.cursor()
    if enabled_only:
        c.execute("SELECT * FROM intervals WHERE enabled = 1")
    else:
        c.execute("SELECT * FROM intervals ORDER BY created_at DESC")
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_interval(iid: int, data: dict):
    conn = get_connection()
    c = conn.cursor()
    fields = []
    values = []
    for key in (
        "title", "content", "interval_minutes", "start_time", "end_time",
        "enabled", "is_paused", "last_triggered", "sound_type", "volume",
    ):
        if key in data:
            fields.append(f"{key} = ?")
            if key == "enabled":
                values.append(1 if data[key] else 0)
            elif key == "is_paused":
                values.append(1 if data[key] else 0)
            else:
                values.append(data[key])
    if fields:
        values.append(iid)
        c.execute(
            f"UPDATE intervals SET {', '.join(fields)} WHERE id = ?", values
        )
        conn.commit()
    conn.close()


def delete_interval(iid: int):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM intervals WHERE id = ?", (iid,))
    conn.commit()
    conn.close()


def add_history(data: dict) -> int:
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        """INSERT INTO history (title, content, reminder_type, triggered_at, is_read)
           VALUES (?, ?, ?, ?, 0)""",
        (
            data["title"],
            data.get("content", ""),
            data["reminder_type"],
            data.get("triggered_at", datetime.now().isoformat()),
        ),
    )
    hid = c.lastrowid
    conn.commit()
    conn.close()
    return hid


def get_history(date_filter=None, unread_only=False):
    conn = get_connection()
    c = conn.cursor()
    query = "SELECT * FROM history"
    conditions = []
    params = []
    if date_filter:
        conditions.append("DATE(triggered_at) = ?")
        params.append(date_filter)
    if unread_only:
        conditions.append("is_read = 0")
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY triggered_at DESC"
    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def mark_history_read(hid: int):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE history SET is_read = 1 WHERE id = ?", (hid,))
    conn.commit()
    conn.close()


def mark_all_history_read():
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE history SET is_read = 1 WHERE is_read = 0")
    conn.commit()
    conn.close()


def delete_history(hid: int):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM history WHERE id = ?", (hid,))
    conn.commit()
    conn.close()


def clear_history():
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM history")
    conn.commit()
    conn.close()
