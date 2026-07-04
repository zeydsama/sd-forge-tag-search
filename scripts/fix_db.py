import os
import sqlite3
import shutil

ROOT_DB = "E:/sd-webui-forge-neo/extensions/sd-forge-tag-search/tag_search.db"
SCRIPT_DB = "E:/sd-webui-forge-neo/extensions/sd-forge-tag-search/scripts/tag_search.db"

# Merge if SCRIPT_DB has stuff ROOT doesn't, but more importantly, ensure ROOT_DB has meta
conn = sqlite3.connect(ROOT_DB)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, val TEXT)''')
conn.commit()

# copy whatever was in SCRIPT_DB meta to ROOT_DB meta just to preserve their button click
try:
    if os.path.exists(SCRIPT_DB):
        conn2 = sqlite3.connect(SCRIPT_DB)
        c2 = conn2.cursor()
        c2.execute("SELECT val FROM meta WHERE key = 'last_indexed'")
        row = c2.fetchone()
        conn2.close()
        
        if row:
            c.execute("INSERT OR REPLACE INTO meta (key, val) VALUES (?, ?)", ('last_indexed', row[0]))
            conn.commit()
            print("Migrated timestamp:", row[0])
except Exception as e:
    print("Migration err:", e)

conn.close()
