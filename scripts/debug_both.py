import sqlite3
for db in ["E:/sd-webui-forge-neo/extensions/sd-forge-tag-search/tag_search.db", "E:/sd-webui-forge-neo/extensions/sd-forge-tag-search/scripts/tag_search.db"]:
    print("DB:", db)
    try:
        conn = sqlite3.connect(db)
        c = conn.cursor()
        c.execute("SELECT count(*) FROM images")
        print(" Images count:", c.fetchone()[0])
        c.execute("SELECT val FROM meta WHERE key='last_indexed'")
        print(" Meta:", c.fetchone())
    except Exception as e:
        print(" Error:", e)
