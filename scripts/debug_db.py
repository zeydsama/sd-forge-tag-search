import os
import sqlite3
import traceback

DB_PATH = r"E:\sd-webui-forge-neo\extensions\sd-forge-tag-search\scripts\tag_search.db"
if not os.path.exists(DB_PATH):
    print("DB does not exist.")
else:
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = c.fetchall()
        print("Tables:", tables)
        
        c.execute("SELECT * FROM meta")
        print("Meta table rows:", c.fetchall())
        conn.close()
    except Exception as e:
        print("Error:", e, traceback.format_exc())
