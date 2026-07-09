"""
Migration v2 -> v3: adds the settings key-value table.
Seeds defaults for salary anchor, balance floor, and opening balance.
Idempotent — safe to re-run.

Run:  python -m db.migrate_v3
"""

import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()
DB_PATH = os.getenv("DB_PATH", "data/finance.db")

DEFAULTS = {
    # Day of month salary lands (~25th). Engine auto-detects from data,
    # this is the manual override / fallback.
    "salary_day": "25",
    # Weeks where closing balance drops below this get a crunch-week flag.
    "balance_floor": "10000",
    # Current actual cash across all bank accounts — the forecast's anchor.
    # UPDATE THIS in Settings before trusting any forecast numbers.
    "opening_balance": "0",
    # 'financial' (salary-to-salary) or 'calendar'
    "month_mode": "financial",
}


def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    for k, v in DEFAULTS.items():
        cur.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))

    conn.commit()

    print("Settings table ready. Current values:")
    for k, v in cur.execute("SELECT key, value FROM settings"):
        print(f"  {k} = {v}")
    conn.close()


if __name__ == "__main__":
    main()