import sqlite3

conn = sqlite3.connect("data/finance.db")
cur = conn.cursor()

n_txn = cur.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
n_acc = cur.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]
n_stm = cur.execute("SELECT COUNT(*) FROM statements").fetchone()[0]

inflow  = cur.execute("SELECT COALESCE(SUM(amount),0) FROM transactions WHERE amount > 0").fetchone()[0]
outflow = cur.execute("SELECT COALESCE(SUM(amount),0) FROM transactions WHERE amount < 0").fetchone()[0]

print(f"Accounts   : {n_acc}")
print(f"Statements : {n_stm}")
print(f"Transactions: {n_txn}")
print(f"Inflows    : Rs. {inflow:,.2f}")
print(f"Outflows   : Rs. {outflow:,.2f}\n")

print(f"{'Date':<12} {'Amount':>14}  Description")
print("-" * 65)
for d, a, desc in cur.execute(
    "SELECT txn_date, amount, description FROM transactions ORDER BY txn_date DESC LIMIT 8"
):
    print(f"{d:<12} Rs.{a:>11,.2f}  {(desc or '')[:38]}")

conn.close()