import sqlite3
import os

DB_PATH = "E:/sd-webui-forge-neo/extensions/sd-forge-tag-search/tag_search.db"
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()
c.execute("SELECT timestamp FROM images LIMIT 5")
print("Timestamps:", c.fetchall())

# Count images with null timestamp
c.execute("SELECT count(*) FROM images WHERE timestamp IS NULL")
print("Null timestamps:", c.fetchone()[0])
conn.close()
