import sqlite3

conn = sqlite3.connect("data/finance.db")
conn.execute("DROP TABLE IF EXISTS categories")
conn.commit()
conn.close()
print("Dropped: categories")