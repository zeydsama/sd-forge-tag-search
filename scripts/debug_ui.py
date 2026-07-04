import os
import sqlite3
import traceback

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tag_search.db")

def get_last_indexed():
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT val FROM meta WHERE key = 'last_indexed'")
        row = c.fetchone()
        conn.close()
        return row[0] if row else "Never (or tracking not started)"
    except Exception as e:
        return f"Never ({e})"

print(get_last_indexed())
