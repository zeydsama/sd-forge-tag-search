import sqlite3

DB_PATH = "E:/sd-webui-forge-neo/extensions/sd-forge-tag-search/tag_search.db"
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

c.execute("SELECT count(*) FROM images WHERE timestamp >= '2026-07-01 00:00:00'")
print("Images since July 1:", c.fetchone()[0])

c.execute("SELECT count(*) FROM images WHERE timestamp >= '2026-07-05 00:00:00'")
print("Images since July 5:", c.fetchone()[0])

conn.close()
