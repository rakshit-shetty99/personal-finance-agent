"""
Dedup hashing — v2 formula. MUST stay identical to db/migrate_v2.py.

Includes account_id so the same amount/date/description on two
different accounts is correctly treated as two transactions.
"""

import hashlib


def make_dedup_hash(account_id: int, txn_date: str, amount: float, raw_desc: str) -> str:
    raw = f"{account_id}|{txn_date}|{abs(round(amount, 2))}|{raw_desc.strip().lower()}"
    return hashlib.sha256(raw.encode()).hexdigest()