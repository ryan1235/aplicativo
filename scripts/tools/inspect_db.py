import sqlite3

db = sqlite3.connect('update64.db')
tables = [t[0] for t in db.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()]

for t in tables:
    columns = [col[1] for col in db.execute(f"PRAGMA table_info({t});").fetchall()]
    if any('x' in c.lower() or 'y' in c.lower() for c in columns):
        print(f"Table: {t}")
        print(f"Columns: {columns}")
        rows = db.execute(f"SELECT * FROM {t} LIMIT 1").fetchall()
        for r in rows:
            print(r)
        print("---")
