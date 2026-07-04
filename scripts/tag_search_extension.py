import os
import sqlite3
import gradio as gr
from PIL import Image
import modules.scripts as scripts
from modules import script_callbacks, shared
from modules.images import read_info_from_image

# Resolve DB path locally in the extension folder
DB_PATH = os.path.join(scripts.basedir(), "tag_search.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS images
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  filepath TEXT UNIQUE,
                  positive TEXT,
                  negative TEXT,
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

def add_image_to_db(filepath, positive, negative):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO images (filepath, positive, negative)
                     VALUES (?, ?, ?)''', (filepath, positive, negative))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[Tag Search] DB Insert error: {e}")

def search_db(query):
    if not query.strip():
        return []
        
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    tags = [t.strip().lower() for t in query.split(",") if t.strip()]
    
    base_query = 'SELECT filepath FROM images WHERE 1=1'
    params = []
    
    for tag in tags:
        if tag.startswith('-'):
            clean_tag = tag[1:]
            base_query += ' AND positive NOT LIKE ?'
            params.append(f'%{clean_tag}%')
        else:
            base_query += ' AND positive LIKE ?'
            params.append(f'%{tag}%')
            
    base_query += ' ORDER BY timestamp DESC LIMIT 300'
            
    c.execute(base_query, params)
    
    # Verify file actually exists before sending to Gallery
    results = []
    for row in c.fetchall():
        path = row[0]
        if os.path.exists(path):
            results.append(path)
            
    conn.close()
    return results

def scan_folder(folder):
    if not os.path.isdir(folder):
        return f"<b style='color:red;'>Error: Folder {folder} not found.</b>"
        
    count = 0
    # Walk directory to find images
    for root, dirs, files in os.walk(folder):
        for file in files:
            if file.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                ext_path = os.path.join(root, file)
                try:
                    img = Image.open(ext_path)
                    text, _ = read_info_from_image(img)
                    if text:
                        pos = ""
                        neg = ""
                        if "Negative prompt:" in text:
                            parts = text.split("Negative prompt:")
                            pos = parts[0].strip().lower()
                            neg = parts[1].split("Steps:")[0].strip().lower() if len(parts) > 1 else ""
                        else:
                            pos = text.split("Steps:")[0].strip().lower()
                            
                        add_image_to_db(ext_path, pos, neg)
                        count += 1
                except Exception as e:
                    pass
                    
    return f"<b style='color:green;'>Successfully scanned and indexed {count} new images.</b>"

def on_image_saved(params):
    try:
        filepath = params.filename
        if params.p:
            pos = getattr(params.p, "prompt", "").lower()
            neg = getattr(params.p, "negative_prompt", "").lower()
            add_image_to_db(filepath, pos, neg)
    except Exception as e:
        print(f"[Tag Search] Auto-index error: {e}")

def on_ui_tabs():
    with gr.Blocks(analytics_enabled=False) as tag_search_interface:
        with gr.Row():
            with gr.Column(scale=1, min_width=300):
                gr.Markdown("### 🔍 Indexed Tag Search")
                gr.Markdown("Search local parameters instantly. Tags are comma separated. Use `-` to exclude (e.g. `1girl, outdoors, -nsfw`).")
                
                search_query = gr.Textbox(label="Search Query", placeholder="1girl, -nsfw...")
                search_btn = gr.Button("Search", variant="primary")
                
                gr.HTML("<hr style='margin: 20px 0;'>")
                
                gr.Markdown("### 📂 Folder Scanner")
                gr.Markdown("Generations are auto-indexed. Use this to back-index prior output folders.")
                scan_folder_input = gr.Textbox(label="Target Folder", value=r"C:\txt2img-images")
                scan_btn = gr.Button("Index Folder", size="sm")
                scan_result = gr.HTML()
                
            with gr.Column(scale=3):
                results_gallery = gr.Gallery(label="Results", show_label=True, elem_id="tag_search_results", columns=4, height=800, object_fit="contain")

        # Event bindings
        search_btn.click(fn=search_db, inputs=[search_query], outputs=[results_gallery])
        search_query.submit(fn=search_db, inputs=[search_query], outputs=[results_gallery])
        scan_btn.click(fn=scan_folder, inputs=[scan_folder_input], outputs=[scan_result])
        
    return [(tag_search_interface, "Tag Search", "tag_search_tab")]

# Initialize routine
init_db()
script_callbacks.on_image_saved(on_image_saved)
script_callbacks.on_ui_tabs(on_ui_tabs)
