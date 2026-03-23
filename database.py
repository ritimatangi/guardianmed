import sqlite3
import json
import os
from datetime import datetime, timedelta
import random

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'medicines.db')


def get_db():
    """Get a database connection."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """Initialize the database schema."""
    conn = get_db()
    cur = conn.cursor()

    cur.execute('''CREATE TABLE IF NOT EXISTS medicines (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        dose TEXT NOT NULL,
        frequency TEXT NOT NULL,
        times TEXT NOT NULL,
        drug_class TEXT,
        notes TEXT,
        active INTEGER DEFAULT 1,
        created_at TEXT DEFAULT (datetime('now'))
    )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS dose_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        medicine_id INTEGER NOT NULL,
        scheduled_time TEXT NOT NULL,
        taken_at TEXT,
        status TEXT NOT NULL,
        logged_by TEXT,
        date TEXT NOT NULL,
        FOREIGN KEY (medicine_id) REFERENCES medicines(id)
    )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS guardian_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_type TEXT,
        description TEXT,
        score_before INTEGER,
        score_after INTEGER,
        reason_chain TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    )''')

    conn.commit()
    conn.close()


def db_is_empty():
    """Check if the medicines table has any rows."""
    conn = get_db()
    count = conn.execute("SELECT COUNT(*) FROM medicines").fetchone()[0]
    conn.close()
    return count == 0


def seed_demo_data():
    """Preload demo patient data with 7-day dose history."""
    conn = get_db()
    cur = conn.cursor()

    # ── Medicines ──────────────────────────────────────────
    medicines = [
        ("Metformin",    "500mg", "twice daily",  '["08:00","20:00"]', "biguanide",     "For diabetes management"),
        ("Aspirin",      "75mg",  "once daily",   '["09:00"]',        "nsaid",          "Blood thinner"),
        ("Lisinopril",   "10mg",  "once daily",   '["08:30"]',        "ace_inhibitor",  "Blood pressure control"),
        ("Simvastatin",  "20mg",  "once daily",   '["21:00"]',        "statin",         "Cholesterol management"),
        ("Metoprolol",   "25mg",  "twice daily",  '["08:00","18:00"]',"beta_blocker",   "Heart rate control"),
    ]

    for m in medicines:
        cur.execute(
            "INSERT INTO medicines (name, dose, frequency, times, drug_class, notes) VALUES (?,?,?,?,?,?)", m
        )
    conn.commit()

    # ── 7-day dose log ─────────────────────────────────────
    today = datetime.now().date()
    med_rows = conn.execute("SELECT id, times FROM medicines").fetchall()

    # Pre-defined patterns to give score ~62
    # day_offset 0 = today, -1 = yesterday, …
    # status_map[day_offset][(med_id, time_slot)] = status
    random.seed(42)

    for day_offset in range(-6, 1):
        day = today + timedelta(days=day_offset)
        day_str = day.isoformat()

        for row in med_rows:
            med_id = row['id']
            times = json.loads(row['times'])

            for t in times:
                # Determine status with weighted randomness to get ~62 score
                r = random.random()
                if day_offset == 0:
                    # Today: ALL doses start as "upcoming"
                    # auto_miss_overdue() will mark past-due ones as "missed"
                    # dynamically when the schedule API is called
                    status = "upcoming"
                    taken_at = None
                elif day_offset in (-1, -3):
                    # Worse days – more misses
                    if r < 0.4:
                        status = "taken"
                        taken_at = f"{day_str} {t}:00"
                    elif r < 0.6:
                        status = "late"
                        # Late by 1-3 hours
                        h, m_part = t.split(":")
                        late_h = int(h) + random.randint(1, 3)
                        taken_at = f"{day_str} {min(late_h,23):02d}:{m_part}:00"
                    else:
                        status = "missed"
                        taken_at = None
                elif day_offset == -5:
                    # Good day
                    if r < 0.9:
                        status = "taken"
                        taken_at = f"{day_str} {t}:00"
                    else:
                        status = "late"
                        h, m_part = t.split(":")
                        late_h = int(h) + 1
                        taken_at = f"{day_str} {min(late_h,23):02d}:{m_part}:00"
                else:
                    # Average days
                    if r < 0.6:
                        status = "taken"
                        taken_at = f"{day_str} {t}:00"
                    elif r < 0.75:
                        status = "late"
                        h, m_part = t.split(":")
                        late_h = int(h) + random.randint(1, 2)
                        taken_at = f"{day_str} {min(late_h,23):02d}:{m_part}:00"
                    else:
                        status = "missed"
                        taken_at = None

                cur.execute(
                    """INSERT INTO dose_log
                       (medicine_id, scheduled_time, taken_at, status, logged_by, date)
                       VALUES (?,?,?,?,?,?)""",
                    (med_id, t, taken_at, status, "system", day_str)
                )

    conn.commit()

    # Seed a couple of guardian events
    cur.execute(
        """INSERT INTO guardian_events (event_type, description, score_before, score_after, reason_chain)
           VALUES (?,?,?,?,?)""",
        ("score_change", "Initial demo score computed", None, 62,
         json.dumps(["Demo data loaded", "7-day history seeded"]))
    )

    conn.commit()
    conn.close()


# ── Helper functions ──────────────────────────────────────

def get_all_medicines(active_only=True):
    conn = get_db()
    if active_only:
        rows = conn.execute("SELECT * FROM medicines WHERE active = 1 ORDER BY name").fetchall()
    else:
        rows = conn.execute("SELECT * FROM medicines ORDER BY name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_medicine(med_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM medicines WHERE id = ?", (med_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def add_medicine(data):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO medicines (name, dose, frequency, times, drug_class, notes)
           VALUES (?,?,?,?,?,?)""",
        (data['name'], data['dose'], data['frequency'],
         json.dumps(data.get('times', [])),
         data.get('drug_class', ''), data.get('notes', ''))
    )
    conn.commit()
    med_id = cur.lastrowid

    # Create today's schedule entries for the new medicine
    today = datetime.now().date().isoformat()
    times = data.get('times', [])
    for t in times:
        cur.execute(
            """INSERT INTO dose_log (medicine_id, scheduled_time, status, logged_by, date)
               VALUES (?,?,?,?,?)""",
            (med_id, t, 'upcoming', 'system', today)
        )
    conn.commit()
    conn.close()
    return med_id


def update_medicine(med_id, data):
    conn = get_db()
    conn.execute(
        """UPDATE medicines SET name=?, dose=?, frequency=?, times=?, drug_class=?, notes=?
           WHERE id=?""",
        (data['name'], data['dose'], data['frequency'],
         json.dumps(data.get('times', [])),
         data.get('drug_class', ''), data.get('notes', ''),
         med_id)
    )
    conn.commit()
    conn.close()


def delete_medicine(med_id):
    conn = get_db()
    conn.execute("UPDATE medicines SET active = 0 WHERE id = ?", (med_id,))
    conn.commit()
    conn.close()


def get_today_schedule():
    """Return today's dose log joined with medicine info."""
    conn = get_db()
    today = datetime.now().date().isoformat()
    rows = conn.execute(
        """SELECT dl.id as log_id, dl.medicine_id, dl.scheduled_time, dl.taken_at,
                  dl.status, m.name, m.dose, m.drug_class
           FROM dose_log dl
           JOIN medicines m ON dl.medicine_id = m.id
           WHERE dl.date = ? AND m.active = 1
           ORDER BY dl.scheduled_time""",
        (today,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def log_dose(log_id, status, taken_at=None):
    """Update a dose log entry.
    
    Args:
        log_id: ID of the dose_log entry
        status: 'taken', 'missed', 'due', 'upcoming', etc.
        taken_at: Optional timestamp (defaults to NOW if status='taken')
    """
    conn = get_db()
    
    # Only set taken_at for taken/late statuses, and only if not already set
    if status in ('taken', 'late'):
        if taken_at is None:
            taken_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn.execute(
            "UPDATE dose_log SET status=?, taken_at=?, logged_by=? WHERE id=?",
            (status, taken_at, 'user', log_id)
        )
    else:
        # For missed or other statuses, don't set taken_at
        conn.execute(
            "UPDATE dose_log SET status=?, logged_by=? WHERE id=?",
            (status, 'user', log_id)
        )
    
    conn.commit()
    conn.close()


def get_dose_logs(days=7):
    """Get dose log for the last N days."""
    conn = get_db()
    start_date = (datetime.now().date() - timedelta(days=days - 1)).isoformat()
    rows = conn.execute(
        """SELECT dl.*, m.name as medicine_name, m.dose as medicine_dose
           FROM dose_log dl
           JOIN medicines m ON dl.medicine_id = m.id
           WHERE dl.date >= ?
           ORDER BY dl.date, dl.scheduled_time""",
        (start_date,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_guardian_event(event_type, description, score_before, score_after, reason_chain):
    conn = get_db()
    conn.execute(
        """INSERT INTO guardian_events (event_type, description, score_before, score_after, reason_chain)
           VALUES (?,?,?,?,?)""",
        (event_type, description, score_before, score_after, json.dumps(reason_chain))
    )
    conn.commit()
    conn.close()


def get_recent_events(limit=20):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM guardian_events ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def auto_miss_overdue():
    """Mark 'upcoming' doses as 'due' or 'missed' based on time window.
    
    - 'due': current time is within 30 mins AFTER scheduled time
    - 'missed': current time is > 30 mins AFTER scheduled time AND not taken
    """
    conn = get_db()
    today = datetime.now().date().isoformat()
    now = datetime.now()
    now_time = now.time()
    
    # Get all upcoming doses for today
    rows = conn.execute(
        """SELECT id, scheduled_time FROM dose_log
           WHERE date = ? AND status = 'upcoming'""",
        (today,)
    ).fetchall()
    
    for row in rows:
        try:
            sched_h, sched_m = map(int, row['scheduled_time'].split(':'))
            scheduled_dt = datetime.combine(now.date(), datetime.min.time().replace(hour=sched_h, minute=sched_m))
            time_diff_minutes = (now - scheduled_dt).total_seconds() / 60
            
            # If past scheduled time by more than 30 mins → missed
            if time_diff_minutes > 30:
                conn.execute("UPDATE dose_log SET status = 'missed' WHERE id = ?", (row['id'],))
            # If within 30 mins after scheduled time → due
            elif time_diff_minutes >= 0:
                conn.execute("UPDATE dose_log SET status = 'due' WHERE id = ?", (row['id'],))
        except (ValueError, TypeError):
            pass
    
    conn.commit()
    conn.close()


def seed_today_schedule():
    """Create today's schedule for all active medicines if not already present."""
    conn = get_db()
    today = datetime.now().date().isoformat()
    
    # Check if today's schedule already exists
    existing = conn.execute(
        "SELECT COUNT(*) FROM dose_log WHERE date = ?", 
        (today,)
    ).fetchone()[0]
    
    if existing > 0:
        conn.close()
        return  # Already populated
    
    # Get all active medicines
    medicines = conn.execute(
        "SELECT id, times FROM medicines WHERE active = 1"
    ).fetchall()
    
    if not medicines:
        conn.close()
        return
    
    # Create today's schedule
    for med_row in medicines:
        med_id = med_row['id']
        times = json.loads(med_row['times'])
        
        for scheduled_time in times:
            conn.execute(
                """INSERT INTO dose_log 
                   (medicine_id, scheduled_time, status, logged_by, date)
                   VALUES (?, ?, ?, ?, ?)""",
                (med_id, scheduled_time, 'upcoming', 'system', today)
            )
    
    conn.commit()
    conn.close()
