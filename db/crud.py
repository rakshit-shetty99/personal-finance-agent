from sqlalchemy.orm import Session
from db.schema import Transaction, Account, get_engine
from db.deduplicator import make_transaction_hash, is_duplicate
from parsers.normaliser import NormalisedTransaction


def get_or_create_account(session: Session, bank: str, account_type: str) -> Account:
    """Gets existing account row or creates it on first import."""
    account = session.query(Account).filter_by(
        bank=bank, account_type=account_type
    ).first()

    if not account:
        account = Account(
            name          = f"{bank} {account_type.title()}",
            account_type  = account_type,
            bank          = bank,
            masked_number = "XXXX"
        )
        session.add(account)
        session.flush()
        print(f"Created account: {account.name}")

    return account


def insert_transactions(
    transactions: list[NormalisedTransaction],
    bank: str = "Kotak",
    account_type: str = "savings"
) -> dict:
    """
    Writes NormalisedTransaction objects to SQLite.
    Skips any transaction whose hash already exists — safe to re-run.
    Returns inserted and skipped counts.
    """
    engine   = get_engine()
    inserted = 0
    skipped  = 0

    with Session(engine) as session:
        account = get_or_create_account(session, bank, account_type)

        for t in transactions:
            txn_hash = make_transaction_hash(
                str(t.date), t.amount, t.raw_description
            )

            if is_duplicate(session, txn_hash):
                skipped += 1
                continue

            txn = Transaction(
                date            = t.date,
                description     = t.description,
                raw_description = t.raw_description,
                amount          = t.amount,
                txn_type        = t.txn_type,
                source          = t.source,
                account_id      = account.id,
                hash            = txn_hash,
                confidence      = 0.0,
            )
            session.add(txn)
            inserted += 1

        session.commit()

    print(f"Import complete: {inserted} inserted, {skipped} duplicates skipped")
    return {"inserted": inserted, "skipped": skipped}