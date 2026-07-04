import os
import sqlite3
import gradio as gr
from PIL import Image
from modules import script_callbacks, shared
from modules.images import read_info_from_image
import traceback

# Hard-lock DB path to this exact script folder
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
            if clean_tag:
                base_query += ' AND positive NOT LIKE ? AND negative NOT LIKE ?'
                params.extend([f'%{clean_tag}%', f'%{clean_tag}%'])
        else:
            base_query += ' AND (positive LIKE ? OR negative LIKE ?)'
            params.extend([f'%{tag}%', f'%{tag}%'])
            
    base_query += ' ORDER BY timestamp DESC LIMIT 300'
            
    c.execute(base_query, params)
    
    results = []
    for row in c.fetchall():
        path = row[0]
        if os.path.exists(path):
            results.append(path)
            
    conn.close()
    return results

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
    result_msg = ""
    if not os.path.isdir(folder):
        print(f"[Tag Search] Error: folder {folder} not found.")
        return f"Error: Folder {folder} not found."
        
    count = 0
    print(f"[Tag Search] Scanning folder: {folder}")
    try:
        for root, dirs, files in os.walk(folder):
            for file in files:
                if file.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                    ext_path = os.path.join(root, file)
                    try:
                        img = Image.open(ext_path)
                        text, _ = read_info_from_image(img)
                        if text:
                            pos, neg = extract_tags(text)
                            add_image_to_db(ext_path, pos, neg)
                            count += 1
                    except Exception as img_e:
                        pass
                        
        print(f"[Tag Search] Finished scan. Indexed {count} images.")
        result_msg = f"Successfully scanned and indexed {count} new images."
    except Exception as e:
        print(f"[Tag Search] Scan error: {traceback.format_exc()}")
        result_msg = f"Error scanning: {e}"
        
    return result_msg

def on_image_saved(params):
    try:
        filepath = params.filename
        if getattr(params, "p", None):
            pos = getattr(params.p, "prompt", "").lower()
            neg = getattr(params.p, "negative_prompt", "").lower()
            add_image_to_db(filepath, pos, neg)
        elif getattr(params, "pnginfo", None) and "parameters" in params.pnginfo:
            pos, neg = extract_tags(params.pnginfo["parameters"])
            add_image_to_db(filepath, pos, neg)
    except Exception as e:
        print(f"[Tag Search] Auto-index error: {e}")

def on_ui_tabs():
    with gr.Blocks(analytics_enabled=False) as tag_search_interface:
        with gr.Row():
            with gr.Column(scale=1, min_width=300):
                gr.Markdown("### 🔍 Indexed Tag Search")
                gr.Markdown("Searches anywhere in the prompt string. Ex: `green, -nsfw` matches 'magragreen' & 'green hair' but excludes 'nsfw'.")
                
                search_query = gr.Textbox(label="Search Query", placeholder="green, -nsfw")
                search_btn = gr.Button("Search", variant="primary")
                
                gr.HTML("<hr style='margin: 20px 0;'>")
                
                gr.Markdown("### 📂 Folder Scanner")
                gr.Markdown("Generations are auto-indexed. Use this to back-index prior output folders.")
                scan_folder_input = gr.Textbox(label="Target Folder", value=r"C:\txt2img-images")
                scan_btn = gr.Button("Index Folder", size="sm")
                scan_result = gr.Textbox(label="Status", interactive=False)
                
            with gr.Column(scale=3):
                results_gallery = gr.Gallery(label="Results", show_label=True, elem_id="tag_search_results", columns=5, height=800, object_fit="contain")

        search_btn.click(fn=search_db, inputs=[search_query], outputs=[results_gallery])
        search_query.submit(fn=search_db, inputs=[search_query], outputs=[results_gallery])
        scan_btn.click(fn=scan_folder, inputs=[scan_folder_input], outputs=[scan_result])
        
    return [(tag_search_interface, "Tag Search", "tag_search_tab")]

init_db()
script_callbacks.on_image_saved(on_image_saved)
script_callbacks.on_ui_tabs(on_ui_tabs)
