import hashlib


def make_transaction_hash(date: str, amount: float, description: str) -> str:
    """
    Creates a unique fingerprint per transaction using date + amount + description.
    If you re-upload the same statement, duplicate rows are detected and skipped.
    We do NOT use account numbers in the hash — keeps it PII-free.
    """
    raw = f"{date}|{round(amount, 2)}|{description.strip().lower()}"
    return hashlib.sha256(raw.encode()).hexdigest()


def is_duplicate(session, hash_value: str) -> bool:
    """
    Returns True if this transaction hash already exists in the DB.
    Used before every insert to prevent duplicates.
    """
    from db.schema import Transaction
    existing = session.query(Transaction).filter_by(hash=hash_value).first()
    return existing is not None