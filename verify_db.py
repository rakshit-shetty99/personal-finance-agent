from sqlalchemy.orm import Session
from db.schema import Transaction, get_engine

engine = get_engine()

with Session(engine) as s:
    total = s.query(Transaction).count()
    print("Total transactions in DB:", total)
    print()

    txns = s.query(Transaction).order_by(Transaction.date.desc()).limit(8).all()
    print(f"{'Date':<12} {'Type':<7} {'Amount':>12}  Description")
    print("-" * 65)
    for t in txns:
        print(f"{str(t.date):<12} {t.txn_type:<7} Rs.{t.amount:>10,.2f}  {t.description[:35]}")