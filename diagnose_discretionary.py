"""
Shows the largest outflows currently counted as 'discretionary' in the
trailing 90 days — so we can build correct exclusion patterns from
real narration text instead of guessing.
"""

import sqlite3
from datetime import date, timedelta

conn = sqlite3.connect("data/finance.db")
cutoff = (date.today() - timedelta(days=90)).isoformat()

rows = conn.execute(
    """SELECT t.txn_date, t.amount, t.description
       FROM transactions t
       JOIN accounts a ON t.account_id = a.id
       WHERE a.type='bank' AND t.amount < 0 AND t.txn_date >= ?
       ORDER BY t.amount ASC
       LIMIT 25""",
    (cutoff,),
).fetchall()

total = conn.execute(
    """SELECT COALESCE(SUM(ABS(t.amount)),0) FROM transactions t
       JOIN accounts a ON t.account_id = a.id
       WHERE a.type='bank' AND t.amount < 0 AND t.txn_date >= ?""",
    (cutoff,),
).fetchone()[0]

print(f"Total bank outflows (trailing 90 days): Rs.{total:,.0f}")
print(f"Implied weekly average: Rs.{total/12.86:,.0f}\n")
print("25 largest outflows (these drive the inflated number):")
print(f"{'Date':<12} {'Amount':>12}  Description")
print("-" * 70)
for d, a, desc in rows:
    print(f"{d:<12} Rs.{abs(a):>10,.0f}  {(desc or '')[:45]}")

conn.close()