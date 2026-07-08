import sqlite3

conn = sqlite3.connect("data/finance.db")
tables = conn.execute(
    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
).fetchall()

print("Tables in database:")
for t in tables:
    print(" -", t[0])

conn.close()