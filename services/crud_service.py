"""
CRUD service layer — all UI database operations live here.
Streamlit pages call these functions; pages never write SQL directly.
"""

import sqlite3
import os
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
DB_PATH = os.getenv("DB_PATH", "data/finance.db")


def _conn():
    return sqlite3.connect(DB_PATH)


# ---------------------------- ACCOUNTS ----------------------------

def get_accounts(include_inactive: bool = False) -> pd.DataFrame:
    q = "SELECT id, name, type, institution, parser_adapter, billing_day, due_day, is_active FROM accounts"
    if not include_inactive:
        q += " WHERE is_active = 1"
    q += " ORDER BY type, name"
    with _conn() as c:
        return pd.read_sql_query(q, c)


def update_account(account_id: int, billing_day, due_day, parser_adapter, is_active: int):
    with _conn() as c:
        c.execute(
            """UPDATE accounts
               SET billing_day = ?, due_day = ?, parser_adapter = ?, is_active = ?
               WHERE id = ?""",
            (billing_day, due_day, parser_adapter, is_active, account_id),
        )
        c.commit()


def add_account(name: str, type_: str, institution: str,
                parser_adapter=None, billing_day=None, due_day=None):
    with _conn() as c:
        c.execute(
            """INSERT INTO accounts (name, type, institution, parser_adapter, billing_day, due_day)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (name, type_, institution, parser_adapter, billing_day, due_day),
        )
        c.commit()


# -------------------------- COMMITMENTS ---------------------------

def get_commitments(include_inactive: bool = False) -> pd.DataFrame:
    q = """
    SELECT cm.id, cm.name, cm.type, cm.amount, cm.frequency,
           cm.due_day, cm.due_date, cm.start_date, cm.end_date,
           src.name AS paid_from, card.name AS linked_card,
           cm.is_active, cm.notes
    FROM commitments cm
    LEFT JOIN accounts src  ON cm.source_account_id = src.id
    LEFT JOIN accounts card ON cm.linked_card_id = card.id
    """
    if not include_inactive:
        q += " WHERE cm.is_active = 1"
    q += " ORDER BY cm.type, cm.due_day"
    with _conn() as c:
        return pd.read_sql_query(q, c)


def add_commitment(name, type_, amount, frequency, due_day=None, due_date=None,
                   start_date=None, end_date=None, source_account_id=None,
                   linked_card_id=None, notes=None):
    with _conn() as c:
        c.execute(
            """INSERT INTO commitments
               (name, type, amount, frequency, due_day, due_date,
                start_date, end_date, source_account_id, linked_card_id, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (name, type_, amount, frequency, due_day, due_date,
             start_date, end_date, source_account_id, linked_card_id, notes),
        )
        c.commit()


def update_commitment(cid, amount, due_day, end_date, is_active, notes):
    with _conn() as c:
        c.execute(
            """UPDATE commitments
               SET amount = ?, due_day = ?, end_date = ?, is_active = ?, notes = ?
               WHERE id = ?""",
            (amount, due_day, end_date, is_active, notes, cid),
        )
        c.commit()


# ---------------------------- SUMMARY ------------------------------

def get_db_summary() -> dict:
    with _conn() as c:
        cur = c.cursor()
        return {
            "accounts":    cur.execute("SELECT COUNT(*) FROM accounts WHERE is_active=1").fetchone()[0],
            "transactions": cur.execute("SELECT COUNT(*) FROM transactions").fetchone()[0],
            "commitments": cur.execute("SELECT COUNT(*) FROM commitments WHERE is_active=1").fetchone()[0],
            "monthly_committed": cur.execute(
                "SELECT COALESCE(SUM(amount),0) FROM commitments WHERE is_active=1 AND frequency='monthly'"
            ).fetchone()[0],
        }