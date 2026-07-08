"""
Import service — the ONLY component that writes transactions to the DB.

Flow: look up account -> resolve adapter from account.parser_adapter ->
parse file -> dedup -> insert -> log to statements table.
"""

import sqlite3
import os
from pathlib import Path
from dotenv import load_dotenv
from parsers.base import get_adapter
from db.deduplicator import make_dedup_hash

load_dotenv()
DB_PATH = os.getenv("DB_PATH", "data/finance.db")


def import_statement(file_path: str, account_name: str) -> dict:
    """
    Imports a statement file for the named account.
    Returns: {"inserted": n, "skipped": n, "status": str}
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # ---- 1. Resolve account + adapter from DB config ----
    row = cur.execute(
        "SELECT id, parser_adapter FROM accounts WHERE name = ? AND is_active = 1",
        (account_name,),
    ).fetchone()

    if row is None:
        conn.close()
        raise ValueError(f"No active account named '{account_name}' in DB.")

    account_id, adapter_key = row
    if not adapter_key:
        conn.close()
        raise ValueError(
            f"Account '{account_name}' has no parser_adapter configured. "
            f"Set it via the Accounts page (or DB) before importing."
        )

    adapter = get_adapter(adapter_key)

    # ---- 2. Parse (adapter never touches DB) ----
    parsed = adapter.parse(file_path)

    # ---- 3. Dedup + insert ----
    inserted, skipped = 0, 0
    for t in parsed:
        h = make_dedup_hash(account_id, t.txn_date, t.amount, t.raw_description)
        exists = cur.execute(
            "SELECT 1 FROM transactions WHERE dedup_hash = ?", (h,)
        ).fetchone()
        if exists:
            skipped += 1
            continue
        cur.execute(
            """INSERT INTO transactions
               (account_id, txn_date, description, raw_description,
                amount, category, source_file, dedup_hash)
               VALUES (?, ?, ?, ?, ?, NULL, ?, ?)""",
            (account_id, t.txn_date, t.description, t.raw_description,
             t.amount, Path(file_path).name, h),
        )
        inserted += 1

    # ---- 4. Log to statements table ----
    dates = [t.txn_date for t in parsed]
    status = "imported" if inserted > 0 else "duplicate"
    cur.execute(
        """INSERT INTO statements
           (account_id, file_name, period_start, period_end, txn_count, status)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (account_id, Path(file_path).name,
         min(dates) if dates else None,
         max(dates) if dates else None,
         inserted, status),
    )

    conn.commit()
    conn.close()

    print(f"Import complete: {inserted} new, {skipped} duplicates skipped")
    return {"inserted": inserted, "skipped": skipped, "status": status}