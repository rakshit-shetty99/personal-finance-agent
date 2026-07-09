import sqlite3
conn = sqlite3.connect("data/finance.db")
conn.execute("UPDATE category_rules SET category='EMI/Loans' WHERE match_pattern='CLG TO'")
conn.execute("""INSERT INTO category_rules (match_pattern, category, priority)
                SELECT 'savesage', 'CC Payment', 10
                WHERE NOT EXISTS (SELECT 1 FROM category_rules WHERE match_pattern='savesage')""")
conn.commit()
print("Rules corrected:", conn.execute(
    "SELECT match_pattern, category FROM category_rules WHERE match_pattern IN ('CLG TO','savesage')"
).fetchall())
conn.close()