"""
Seeds category rules for non-discretionary outflow patterns discovered
in real Kotak narrations. The cashflow engine excludes these categories
from the discretionary projection. Data-driven: add more via DB/UI later.
"""

import sqlite3, os
from dotenv import load_dotenv

load_dotenv()
DB_PATH = os.getenv("DB_PATH", "data/finance.db")

RULES = [
    # (match_pattern, category, priority)
    ("CRED Club",       "CC Payment",  10),
    ("CHEQ DIGITAL",    "CC Payment",  10),
    ("Credit Card Bi",  "CC Payment",  10),
    ("ZERODHA",         "Investments", 10),
    ("ICCL",            "Investments", 10),
    ("SentIMPS",        "Transfers",   20),
    ("FUND IDFC",       "Transfers",   10),
    ("CLG TO",          "Transfers",   30),   # confirm: largest outflow was cheque clearing
    ("NACH",            "EMI/Loans",   10),
    ("Loan Repayment",  "EMI/Loans",   10),
]

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
added = 0
for pattern, category, priority in RULES:
    exists = cur.execute(
        "SELECT 1 FROM category_rules WHERE match_pattern = ?", (pattern,)
    ).fetchone()
    if not exists:
        cur.execute(
            "INSERT INTO category_rules (match_pattern, category, priority) VALUES (?, ?, ?)",
            (pattern, category, priority),
        )
        added += 1
conn.commit()
print(f"Added {added} exclusion rules. Total rules now:",
      cur.execute("SELECT COUNT(*) FROM category_rules").fetchone()[0])
conn.close()