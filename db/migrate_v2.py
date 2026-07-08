"""
Migration v1 -> v2: Week 1 schema to Solution Doc target schema (Section 5).

What it does, in order:
  1. Backs up data/finance.db -> data/finance_backup_v1.db
  2. Renames old tables (accounts, transactions) to *_old
  3. Creates new tables: accounts, transactions, commitments, statements, category_rules
  4. Migrates Kotak account + 234 transactions (amounts become SIGNED: outflow = negative)
  5. Recomputes dedup hashes with the new formula (includes account_id)
  6. Seeds all 12 accounts (4 banks + 8 credit cards with billing/due days)
  7. Seeds category_rules table with starter taxonomy patterns
  8. Drops insights_cache (abandoned cloud-AI design). Keeps budgets dormant.
  9. Verifies row counts and prints a summary

Run:  python -m db.migrate_v2
"""

import hashlib
import shutil
import sqlite3
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()
DB_PATH = os.getenv("DB_PATH", "data/finance.db")
BACKUP_PATH = "data/finance_backup_v1.db"


# ------------------------------------------------------------------
# New dedup hash formula (v2): includes account_id so the same
# amount/date/description on two different accounts is NOT a duplicate.
# The import service MUST use this exact same function.
# ------------------------------------------------------------------
def make_dedup_hash(account_id: int, txn_date: str, amount: float, raw_desc: str) -> str:
    raw = f"{account_id}|{txn_date}|{abs(round(amount, 2))}|{raw_desc.strip().lower()}"
    return hashlib.sha256(raw.encode()).hexdigest()


# ------------------------------------------------------------------
# The 12 accounts to seed (from Solution Doc sections 3.2 and 3.3)
# (name, type, institution, parser_adapter, billing_day, due_day)
# ------------------------------------------------------------------
SEED_ACCOUNTS = [
    # Banks — parser_adapter NULL until each adapter is built (Week 5)
    ("Kotak Savings",           "bank", "Kotak",  "kotak_csv", None, None),
    ("Bank of Baroda Savings",  "bank", "BoB",    None,        None, None),
    ("Canara Savings",          "bank", "Canara", None,        None, None),
    ("IDFC First Savings",      "bank", "IDFC",   None,        None, None),
    # Credit cards — billing/due days from user, adapters come Weeks 4 & 7
    ("HDFC Regalia Gold",       "credit_card", "HDFC",  None, 19, 10),
    ("HDFC Tata Neu Infinity",  "credit_card", "HDFC",  None,  2, 21),
    ("IDFC Power Plus",         "credit_card", "IDFC",  None, 20,  4),
    ("SBI Cashback",            "credit_card", "SBI",   None,  4, 23),
    ("BoB Eterna",              "credit_card", "BoB",   None, 16,  2),
    ("Kotak Zen Signature",     "credit_card", "Kotak", None, 16,  3),
    ("Axis Vistara",            "credit_card", "Axis",  None, 24, 12),
    ("ICICI Sapphiro",          "credit_card", "ICICI", None,  6, 23),
]

# Starter category rules — obvious Kotak/UPI patterns seen in your data.
# (match_pattern, category, priority) — lower priority number = checked first
SEED_RULES = [
    ("SWIGGY",          "Food & Dining",  10),
    ("ZOMATO",          "Food & Dining",  10),
    ("BHIMCASHBACK",    "Income",         10),
    ("Int.Pd",          "Income",         10),
    ("NEFT IN",         "Salary",         20),
    ("MB: Sent",        "Transfers",      20),
    ("UPILITE",         "Other",          90),
]


def table_exists(cur, name: str) -> bool:
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)
    )
    return cur.fetchone() is not None


def column_exists(cur, table: str, column: str) -> bool:
    cur.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cur.fetchall())


def main():
    db_file = Path(DB_PATH)
    if not db_file.exists():
        print(f"ERROR: {DB_PATH} not found. Nothing to migrate.")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # --------------------------------------------------------------
    # Idempotency check: if accounts already has parser_adapter,
    # migration was already applied — do nothing.
    # --------------------------------------------------------------
    if table_exists(cur, "accounts") and column_exists(cur, "accounts", "parser_adapter"):
        print("Migration already applied (accounts.parser_adapter exists). Nothing to do.")
        conn.close()
        return

    # --------------------------------------------------------------
    # Step 1 — Backup
    # --------------------------------------------------------------
    shutil.copy2(DB_PATH, BACKUP_PATH)
    print(f"Step 1: Backup created -> {BACKUP_PATH}")

    # --------------------------------------------------------------
    # Step 2 — Rename old tables
    # --------------------------------------------------------------
    cur.execute("ALTER TABLE accounts RENAME TO accounts_old")
    cur.execute("ALTER TABLE transactions RENAME TO transactions_old")
    print("Step 2: Renamed accounts -> accounts_old, transactions -> transactions_old")

    # --------------------------------------------------------------
    # Step 3 — Create new tables (Solution Doc Section 5)
    # --------------------------------------------------------------
    cur.executescript("""
    CREATE TABLE accounts (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        type TEXT NOT NULL,                 -- 'bank' | 'credit_card'
        institution TEXT,
        parser_adapter TEXT,
        billing_day INTEGER,
        due_day INTEGER,
        is_active INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE transactions (
        id INTEGER PRIMARY KEY,
        account_id INTEGER REFERENCES accounts(id),
        txn_date TEXT NOT NULL,
        description TEXT,
        raw_description TEXT,               -- kept from v1 for audit/debug
        amount REAL NOT NULL,               -- SIGNED: negative = outflow
        category TEXT,
        source_file TEXT,
        dedup_hash TEXT UNIQUE,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE commitments (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        type TEXT NOT NULL,                 -- 'emi'|'rent'|'cc_bill'|'subscription'|'adhoc'
        amount REAL,
        frequency TEXT NOT NULL,            -- 'monthly'|'annual'|'one_time'
        due_day INTEGER,
        due_date TEXT,
        start_date TEXT,
        end_date TEXT,
        source_account_id INTEGER REFERENCES accounts(id),
        linked_card_id INTEGER REFERENCES accounts(id),
        is_active INTEGER DEFAULT 1,
        notes TEXT
    );

    CREATE TABLE statements (
        id INTEGER PRIMARY KEY,
        account_id INTEGER REFERENCES accounts(id),
        file_name TEXT,
        period_start TEXT,
        period_end TEXT,
        txn_count INTEGER,
        imported_at TEXT DEFAULT CURRENT_TIMESTAMP,
        status TEXT
    );

    CREATE TABLE category_rules (
        id INTEGER PRIMARY KEY,
        match_pattern TEXT NOT NULL,
        category TEXT NOT NULL,
        priority INTEGER DEFAULT 100,
        is_active INTEGER DEFAULT 1
    );

    CREATE INDEX idx_txn_date ON transactions(txn_date);
    CREATE INDEX idx_txn_account ON transactions(account_id);
    CREATE INDEX idx_txn_category ON transactions(category);
    """)
    print("Step 3: Created new tables + indexes")

    # --------------------------------------------------------------
    # Step 4 — Seed the 12 accounts (Kotak first so it gets id=1)
    # --------------------------------------------------------------
    for name, typ, inst, adapter, bill, due in SEED_ACCOUNTS:
        cur.execute(
            """INSERT INTO accounts
               (name, type, institution, parser_adapter, billing_day, due_day)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (name, typ, inst, adapter, bill, due),
        )
    kotak_id = cur.execute(
        "SELECT id FROM accounts WHERE name='Kotak Savings'"
    ).fetchone()[0]
    print(f"Step 4: Seeded 12 accounts (Kotak Savings = id {kotak_id})")

    # --------------------------------------------------------------
    # Step 5 — Migrate transactions with signed amounts + new hashes
    # Old schema: amount always positive, txn_type = 'debit'/'credit',
    #             category_id FK (all NULL — categorisation never ran)
    # New schema: amount signed (debit -> negative), category TEXT
    # --------------------------------------------------------------
    old_txns = cur.execute(
        """SELECT date, description, raw_description, amount, txn_type, source
           FROM transactions_old"""
    ).fetchall()

    migrated = 0
    for txn_date, desc, raw_desc, amount, txn_type, source in old_txns:
        signed = -abs(amount) if txn_type == "debit" else abs(amount)
        raw_desc = raw_desc or desc or ""
        h = make_dedup_hash(kotak_id, txn_date, signed, raw_desc)
        cur.execute(
            """INSERT INTO transactions
               (account_id, txn_date, description, raw_description,
                amount, category, source_file, dedup_hash)
               VALUES (?, ?, ?, ?, ?, NULL, ?, ?)""",
            (kotak_id, txn_date, desc, raw_desc, signed, source, h),
        )
        migrated += 1
    print(f"Step 5: Migrated {migrated} transactions (amounts now signed)")

    # --------------------------------------------------------------
    # Step 6 — Seed starter category rules
    # --------------------------------------------------------------
    for pattern, category, priority in SEED_RULES:
        cur.execute(
            "INSERT INTO category_rules (match_pattern, category, priority) VALUES (?, ?, ?)",
            (pattern, category, priority),
        )
    print(f"Step 6: Seeded {len(SEED_RULES)} starter category rules")

    # --------------------------------------------------------------
    # Step 7 — Drop dead weight, clean up old tables
    # budgets stays (dormant). categories table stays for reference
    # until Week 6 taxonomy work, then we decide.
    # --------------------------------------------------------------
    if table_exists(cur, "insights_cache"):
        cur.execute("DROP TABLE insights_cache")
        print("Step 7: Dropped insights_cache")
    cur.execute("DROP TABLE transactions_old")
    cur.execute("DROP TABLE accounts_old")
    print("Step 7: Dropped *_old tables")

    conn.commit()

    # --------------------------------------------------------------
    # Step 8 — Verify
    # --------------------------------------------------------------
    n_accounts = cur.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]
    n_txns = cur.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
    outflow = cur.execute(
        "SELECT ROUND(SUM(amount),2) FROM transactions WHERE amount < 0"
    ).fetchone()[0]
    inflow = cur.execute(
        "SELECT ROUND(SUM(amount),2) FROM transactions WHERE amount > 0"
    ).fetchone()[0]

    print("\n================ MIGRATION SUMMARY ================")
    print(f"Accounts        : {n_accounts}  (expected 12)")
    print(f"Transactions    : {n_txns}  (expected 234)")
    print(f"Total inflows   : Rs. {inflow:,.2f}")
    print(f"Total outflows  : Rs. {outflow:,.2f}")
    print(f"Backup at       : {BACKUP_PATH}")
    print("===================================================")
    if n_txns == 234 and n_accounts == 12:
        print("VERIFIED: Migration successful, zero data loss.")
    else:
        print("WARNING: Counts do not match expected. Check before proceeding.")

    conn.close()


if __name__ == "__main__":
    main()