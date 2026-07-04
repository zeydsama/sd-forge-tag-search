import os
import sqlite3
import gradio as gr
from PIL import Image
from modules import script_callbacks, shared
from modules.images import read_info_from_image
from datetime import datetime
import traceback

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tag_search.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS images
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  filepath TEXT UNIQUE,
                  positive TEXT,
                  negative TEXT,
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, val TEXT)''')
    conn.commit()
    conn.close()

def get_last_indexed():
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT val FROM meta WHERE key = 'last_indexed'")
        row = c.fetchone()
        conn.close()
        return row[0] if row else "Never (or tracking not started)"
    except Exception:
        return "Never"

def set_last_indexed():
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO meta (key, val) VALUES (?, ?)", ('last_indexed', now))
    conn.commit()
    conn.close()
    return now

def add_image_to_db(filepath, positive, negative, timestamp=None):
    if not timestamp:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO images (filepath, positive, negative, timestamp)
                     VALUES (?, ?, ?, ?)''', (filepath, positive, negative, timestamp))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[Tag Search] DB Insert error: {e}")

def search_db(query, sort_order, date_from, date_to):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    tags = [t.strip().lower() for t in query.split(",") if t.strip()]
    
    base_query = 'SELECT filepath FROM images WHERE 1=1'
    params = []
    
    for tag in tags:
        if tag.startswith('-'):
            clean_tag = tag[1:]
            if clean_tag:
                base_query += ' AND positive NOT LIKE ? AND negative NOT LIKE ?'
                params.extend([f'%{clean_tag}%', f'%{clean_tag}%'])
        else:
            base_query += ' AND (positive LIKE ? OR negative LIKE ?)'
            params.extend([f'%{tag}%', f'%{tag}%'])
            
    if date_from and date_from.strip():
        base_query += ' AND timestamp >= ?'
        params.append(f'{date_from.strip()} 00:00:00')
    if date_to and date_to.strip():
        base_query += ' AND timestamp <= ?'
        params.append(f'{date_to.strip()} 23:59:59')
            
    if sort_order == "Oldest First":
        base_query += ' ORDER BY timestamp ASC LIMIT 300'
    else:
        base_query += ' ORDER BY timestamp DESC LIMIT 300'
        
    c.execute(base_query, params)
    
    results = []
    for row in c.fetchall():
        path = row[0]
        if os.path.exists(path):
            results.append(path)
            
    conn.close()
    return results, results

def extract_tags(text):
    if not text: 
        return "", ""
    text = text.lower()
    
    pos_end = len(text)
    neg_start = text.find("negative prompt:")
    steps_start = text.find("steps:")
    
    neg = ""
    if neg_start != -1:
        pos_end = neg_start
        n_end = steps_start if steps_start != -1 else len(text)
        neg = text[neg_start + 16 : n_end].strip()
    elif steps_start != -1:
        pos_end = steps_start
        
    pos = text[:pos_end].strip()
    return pos, neg

def scan_folder(folder):
    if not os.path.isdir(folder):
        print(f"[Tag Search] Error: folder {folder} not found.")
        return f"Error: Folder {folder} not found.", gr.update()
        
    count = 0
    print(f"[Tag Search] Scanning folder: {folder}")
    try:
        for root, dirs, files in os.walk(folder):
            for file in files:
                if file.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                    ext_path = os.path.join(root, file)
                    try:
                        mtime = os.path.getmtime(ext_path)
                        timestamp = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
                        
                        img = Image.open(ext_path)
                        text, _ = read_info_from_image(img)
                        if text:
                            pos, neg = extract_tags(text)
                            add_image_to_db(ext_path, pos, neg, timestamp)
                            count += 1
                    except Exception:
                        pass
                        
        last_stamp = set_last_indexed()
        print(f"[Tag Search] Finished scan. Indexed {count} images.")
        return f"Successfully scanned and indexed {count} new images.", last_stamp
    except Exception as e:
        print(f"[Tag Search] Scan error: {traceback.format_exc()}")
        return f"Error scanning: {e}", gr.update()

def on_image_saved(params):
    try:
        filepath = params.filename
        
        mtime = os.path.getmtime(filepath)
        timestamp = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")

        if getattr(params, "p", None):
            pos = getattr(params.p, "prompt", "").lower()
            neg = getattr(params.p, "negative_prompt", "").lower()
            add_image_to_db(filepath, pos, neg, timestamp)
        elif getattr(params, "pnginfo", None) and "parameters" in params.pnginfo:
            pos, neg = extract_tags(params.pnginfo["parameters"])
            add_image_to_db(filepath, pos, neg, timestamp)
            
        set_last_indexed()
    except Exception as e:
        print(f"[Tag Search] Auto-index error: {e}")

def get_image_details(evt: gr.SelectData, state_paths):
    idx = evt.index
    if idx < len(state_paths):
        filepath = state_paths[idx]
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT positive, negative FROM images WHERE filepath = ?", (filepath,))
            row = c.fetchone()
            conn.close()
            if row:
                return row[0], row[1]
        except Exception:
            pass
    return "", ""

def on_ui_tabs():
    init_db()
    last_indexed_str = get_last_indexed()
    
    with gr.Blocks(analytics_enabled=False) as tag_search_interface:
        search_results_state = gr.State([])
        
        with gr.Row(equal_height=False):
            with gr.Column(scale=1, min_width=320):
                gr.Markdown("### 🔍 Tag Search Engine")
                
                search_query = gr.Textbox(label="Search Query", placeholder="green hair, -nsfw")
                
                with gr.Row():
                    date_from = gr.Textbox(label="From Date", placeholder="YYYY-MM-DD", scale=1)
                    date_to = gr.Textbox(label="To Date", placeholder="YYYY-MM-DD", scale=1)
                    
                sort_order = gr.Dropdown(label="Sort By", choices=["Newest First", "Oldest First"], value="Newest First")
                search_btn = gr.Button("Search Images", variant="primary")
                
                gr.HTML("<hr style='margin: 15px 0;'>")
                
                gr.Markdown("### 📂 Image Details (Click Image)")
                detail_pos = gr.Textbox(label="Positive Prompt", interactive=False, lines=4)
                detail_neg = gr.Textbox(label="Negative Prompt", interactive=False, lines=3)
                
                gr.HTML("<hr style='margin: 15px 0;'>")
                
                gr.Markdown("### ⚙️ Database Indexer")
                # Visual proof that database persists between restarts
                lbl_last_indexed = gr.Textbox(label="Last Database Index", value=last_indexed_str, interactive=False)
                scan_folder_input = gr.Textbox(label="Target Folder", value=r"C:\txt2img-images")
                scan_btn = gr.Button("Re-Scan Folder", size="sm")
                scan_result = gr.Textbox(label="Scan Output", interactive=False)
                
            with gr.Column(scale=3):
                results_gallery = gr.Gallery(label="Results", show_label=True, elem_id="tag_search_results", columns=5, height=800, object_fit="contain")

        # Events
        inputs_search = [search_query, sort_order, date_from, date_to]
        search_btn.click(fn=search_db, inputs=inputs_search, outputs=[results_gallery, search_results_state])
        search_query.submit(fn=search_db, inputs=inputs_search, outputs=[results_gallery, search_results_state])
        
        # When gallery is clicked, pull details from DB based on state
        results_gallery.select(fn=get_image_details, inputs=[search_results_state], outputs=[detail_pos, detail_neg])
        
        scan_btn.click(fn=scan_folder, inputs=[scan_folder_input], outputs=[scan_result, lbl_last_indexed])
        
    return [(tag_search_interface, "Tag Search", "tag_search_tab")]

init_db()
script_callbacks.on_image_saved(on_image_saved)
script_callbacks.on_ui_tabs(on_ui_tabs)
