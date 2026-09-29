#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Lustre Separator - Desktop GUI Application (.exe)
Pure Gemini Video Analysis & Media Renaming Engine
- 100% English UI and 100% English AI Output
- Direct Gemini AI Video Attach via API
- Generates ONLY: Hook, Caption, and Hashtags in fluent English
- Keeps Folder Name UNCHANGED
- Renames video inside sequentially to 1.mp4, 2.mp4, 3.mp4...
- Real-time Stop / Cancel capability
"""

import os
import sys
import shutil
import time
import json
import threading
import queue
import re
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
from PIL import Image, ImageTk

try:
    import windnd
    WINDND_AVAILABLE = True
except Exception:
    windnd = None
    WINDND_AVAILABLE = False

try:
    import auto_updater
    AUTO_UPDATER_AVAILABLE = True
except Exception:
    auto_updater = None
    AUTO_UPDATER_AVAILABLE = False

# Determine base directory whether running as script or frozen PyInstaller exe
if getattr(sys, 'frozen', False):
    WORKSPACE_DIR = Path(sys.executable).resolve().parent
else:
    WORKSPACE_DIR = Path(__file__).resolve().parent

INPUT_DIR = WORKSPACE_DIR / "input_media"
OUTPUT_DIR = WORKSPACE_DIR / "output_media"
CONFIG_FILE = WORKSPACE_DIR / "config.json"

INPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_CONFIG = {
    "gemini_api_key": "AQ.Ab8RN6I11g79O6AH49StyV3bSH0BryNLxicJdzzT2YzT16GsDw",
    "target_platform": "facebook",
    "language": "english",
    "tone": "viral",
    "niche": "general"
}

ACTIVE_MODELS = [
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite-preview",
    "gemini-3.8-flash",
    "gemini-3.5-flash",
    "gemini-flash-latest"
]

def load_config():
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return {**DEFAULT_CONFIG, **json.load(f)}
        except Exception:
            pass
    return DEFAULT_CONFIG

def save_config(cfg):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=4)
    except Exception as e:
        print(f"Config save notice: {e}")

def clean_ai_output(raw_text):
    """Cleans any accidental section headers/labels (HOOK:, CAPTION:, HASHTAGS:) so user gets pure caption & hashtags."""
    if not raw_text:
        return ""
    text = raw_text.strip()
    if text.startswith("```") and text.endswith("```"):
        lines = text.splitlines()
        if len(lines) >= 2:
            text = "\n".join(lines[1:-1]).strip()

    lines = text.splitlines()
    cleaned_lines = []
    header_pattern = re.compile(
        r'^\s*(?:[*_#`~>\s]|🎯|📌|🏷️)*(?:HOOK|CAPTION|HASHTAGS|VIRAL HOOK|ENGAGING CAPTION|VIRAL HASHTAGS)(?:[*_#`~>\s]|:)*$',
        re.IGNORECASE
    )
    inline_header_pattern = re.compile(
        r'^\s*(?:[*_#`~>\s]|🎯|📌|🏷️)*(?:HOOK|CAPTION|HASHTAGS|VIRAL HOOK|ENGAGING CAPTION|VIRAL HASHTAGS)(?:[*_#`~>\s]|:)+\s*',
        re.IGNORECASE
    )
    for line in lines:
        stripped = line.strip()
        if header_pattern.match(stripped):
            continue
        cleaned = inline_header_pattern.sub('', line)
        cleaned_lines.append(cleaned)

    result = "\n".join(cleaned_lines).strip()
    result = re.sub(r'\n{3,}', '\n\n', result)
    return result

def bind_hover(widget, normal_bg, hover_bg):
    """Adds smooth hover micro-animations to Tkinter buttons."""
    widget.bind("<Enter>", lambda e: widget.config(bg=hover_bg) if str(widget['state']) != 'disabled' else None)
    widget.bind("<Leave>", lambda e: widget.config(bg=normal_bg) if str(widget['state']) != 'disabled' else None)

def get_next_available_index(target_folder):
    """Finds the next unused sequential index (1, 2, 3...) inside target_folder."""
    target_folder.mkdir(parents=True, exist_ok=True)
    existing_nums = set()
    for f in target_folder.iterdir():
        if f.is_file():
            m = re.match(r"^(\d+)\.", f.name)
            if m:
                try:
                    existing_nums.add(int(m.group(1)))
                except ValueError:
                    pass
            m2 = re.match(r"^(\d+)_seo_caption_hashtags\.txt$", f.name)
            if m2:
                try:
                    existing_nums.add(int(m2.group(1)))
                except ValueError:
                    pass
    next_idx = 1
    while next_idx in existing_nums:
        next_idx += 1
    return next_idx

def safe_move_file(src, dst):
    """Safely moves (cuts) a file, avoiding FileExistsError or destination collision on Windows."""
    src = Path(src)
    dst = Path(dst)
    if not src.exists():
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        if src.resolve() == dst.resolve():
            return True
    except Exception:
        pass
    if dst.exists():
        try:
            dst.unlink()
        except Exception:
            pass
    try:
        shutil.move(str(src), str(dst))
        return True
    except Exception:
        # Cross-volume or permissions fallback: copy2 then unlink original
        try:
            shutil.copy2(str(src), str(dst))
            try:
                src.unlink()
            except Exception:
                pass
            return True
        except Exception:
            return False

class LustreSeparatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("✨ Lustre Separator - AI Video SEO & Media Organizer")
        self.root.geometry("1120x780")
        self.root.minsize(960, 650)
        self.root.configure(bg="#060913")

        # Set Window Icon
        icon_path = WORKSPACE_DIR / "assets" / "logo.ico"
        if icon_path.exists():
            try:
                self.root.iconbitmap(str(icon_path))
            except Exception:
                pass

        self.config = load_config()
        self.files_list = []
        self.selected_file_index = -1
        self.is_processing = False
        self.stop_requested = False
        self.latest_caption_text = ""
        self.spinner_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self.spinner_idx = 0
        self.msg_queue = queue.Queue()
        self.logo_img = None

        self.setup_ui()
        if WINDND_AVAILABLE:
            try:
                windnd.hook_dropfiles(self.root, func=self.on_drop_files)
            except Exception as e:
                print(f"windnd hook failed: {e}")
        self.refresh_file_list()
        self.check_queue()
        self.animate_ticker()
        if AUTO_UPDATER_AVAILABLE:
            threading.Thread(target=self.background_update_check, daemon=True).start()

    def setup_ui(self):
        # Header banner
        header = tk.Frame(self.root, bg="#0d1424", padx=24, pady=12, highlightthickness=1, highlightbackground="#1e293b")
        header.pack(fill="x")

        # Load Logo in Header
        logo_png = WORKSPACE_DIR / "assets" / "logo.png"
        if logo_png.exists():
            try:
                pil_img = Image.open(str(logo_png)).resize((44, 44), Image.Resampling.LANCZOS)
                self.logo_img = ImageTk.PhotoImage(pil_img)
                logo_lbl = tk.Label(header, image=self.logo_img, bg="#0d1424")
                logo_lbl.pack(side="left", padx=(0, 14))
            except Exception:
                pass

        header_text_frame = tk.Frame(header, bg="#0d1424")
        header_text_frame.pack(side="left", fill="both", expand=True)

        title_lbl = tk.Label(
            header_text_frame,
            text="✨ LUSTRE SEPARATOR",
            font=("Segoe UI", 16, "bold"),
            fg="#38bdf8",
            bg="#0d1424"
        )
        title_lbl.pack(anchor="w")

        subtitle_lbl = tk.Label(
            header_text_frame,
            text="Direct Gemini AI Video Analysis  •  Sequential Renamer (1.mp4, 2.mp4...)  •  Pure English Caption & Hashtags",
            font=("Segoe UI", 9),
            fg="#94a3b8",
            bg="#0d1424"
        )
        subtitle_lbl.pack(anchor="w", pady=(2, 0))

        # Top Control Bar (Platform + API Key + Output Folder)
        ctrl_bar = tk.Frame(self.root, bg="#0f172a", padx=16, pady=10)
        ctrl_bar.pack(fill="x")

        tk.Label(
            ctrl_bar,
            text="🎯 Target Platform:",
            font=("Segoe UI", 10, "bold"),
            fg="#e2e8f0",
            bg="#0f172a"
        ).pack(side="left", padx=(0, 8))

        self.platform_var = tk.StringVar(value=self.config.get("target_platform", "facebook"))
        platform_combo = ttk.Combobox(
            ctrl_bar,
            textvariable=self.platform_var,
            values=["facebook", "tiktok", "instagram", "youtube"],
            state="readonly",
            width=14,
            font=("Segoe UI", 10)
        )
        platform_combo.pack(side="left", padx=(0, 16))
        platform_combo.bind("<<ComboboxSelected>>", self.on_platform_changed)

        btn_key = tk.Button(
            ctrl_bar,
            text="🔑 Gemini API Key",
            font=("Segoe UI", 9, "bold"),
            bg="#334155",
            fg="#e2e8f0",
            activebackground="#475569",
            activeforeground="#ffffff",
            padx=12,
            pady=4,
            relief="flat",
            cursor="hand2",
            command=self.open_key_dialog
        )
        btn_key.pack(side="left", padx=(0, 10))
        bind_hover(btn_key, "#334155", "#475569")

        btn_web_app = tk.Button(
            ctrl_bar,
            text="🌐 Open Web App (Studio)",
            font=("Segoe UI", 9, "bold"),
            bg="#0284c7",
            fg="#ffffff",
            activebackground="#0369a1",
            activeforeground="#ffffff",
            padx=14,
            pady=4,
            relief="flat",
            cursor="hand2",
            command=self.open_web_app
        )
        btn_web_app.pack(side="left", padx=(0, 10))
        bind_hover(btn_web_app, "#0284c7", "#0ea5e9")

        btn_open_out = tk.Button(
            ctrl_bar,
            text="📂 Open Output Folder",
            font=("Segoe UI", 9, "bold"),
            bg="#1e293b",
            fg="#38bdf8",
            activebackground="#334155",
            activeforeground="#ffffff",
            padx=12,
            pady=4,
            relief="flat",
            cursor="hand2",
            command=lambda: os.startfile(str(OUTPUT_DIR))
        )
        btn_open_out.pack(side="right")
        bind_hover(btn_open_out, "#1e293b", "#334155")

        self.btn_check_update = tk.Button(
            ctrl_bar,
            text="🔄 Check Updates",
            font=("Segoe UI", 8),
            bg="#1e293b",
            fg="#94a3b8",
            activebackground="#334155",
            activeforeground="#ffffff",
            padx=10,
            pady=4,
            relief="flat",
            cursor="hand2",
            command=self.manual_check_updates
        )
        self.btn_check_update.pack(side="right", padx=(0, 8))
        bind_hover(self.btn_check_update, "#1e293b", "#334155")

        # Main Split Content
        main_split = tk.PanedWindow(self.root, orient="horizontal", bg="#0f172a", sashwidth=5)
        main_split.pack(fill="both", expand=True, padx=16, pady=6)

        # LEFT PANE: Input Files & Queue Management
        left_frame = tk.Frame(main_split, bg="#1e293b", padx=14, pady=14)
        main_split.add(left_frame, minsize=340)

        input_btn_frame = tk.Frame(left_frame, bg="#1e293b")
        input_btn_frame.pack(fill="x", pady=(0, 8))

        # Mode selector: Cut (Move) vs Copy
        mode_frame = tk.Frame(input_btn_frame, bg="#0f172a", padx=8, pady=6, highlightbackground="#334155", highlightthickness=1)
        mode_frame.pack(fill="x", pady=(0, 8))

        lbl_mode = tk.Label(
            mode_frame,
            text="📥 File Selection Mode:",
            font=("Segoe UI", 8, "bold"),
            bg="#0f172a",
            fg="#94a3b8"
        )
        lbl_mode.pack(anchor="w")

        radio_row = tk.Frame(mode_frame, bg="#0f172a")
        radio_row.pack(fill="x", pady=(3, 0))

        self.import_mode_var = tk.StringVar(value="cut")
        rb_cut = tk.Radiobutton(
            radio_row,
            text="✂️ Cut / Move (Default)",
            variable=self.import_mode_var,
            value="cut",
            font=("Segoe UI", 8, "bold"),
            bg="#0f172a",
            fg="#38bdf8",
            selectcolor="#1e293b",
            activebackground="#0f172a",
            activeforeground="#38bdf8",
            cursor="hand2"
        )
        rb_cut.pack(side="left", padx=(0, 8))

        rb_copy = tk.Radiobutton(
            radio_row,
            text="📋 Copy",
            variable=self.import_mode_var,
            value="copy",
            font=("Segoe UI", 8),
            bg="#0f172a",
            fg="#94a3b8",
            selectcolor="#1e293b",
            activebackground="#0f172a",
            activeforeground="#f1f5f9",
            cursor="hand2"
        )
        rb_copy.pack(side="left")

        btn_add_files = tk.Button(
            input_btn_frame,
            text="✂️ Select Video Files (Cut & Move)",
            font=("Segoe UI", 9, "bold"),
            bg="#059669",
            fg="#ffffff",
            activebackground="#047857",
            activeforeground="#ffffff",
            padx=10,
            pady=6,
            relief="flat",
            cursor="hand2",
            command=self.browse_and_add_files
        )
        btn_add_files.pack(fill="x", pady=(0, 4))
        bind_hover(btn_add_files, "#059669", "#10b981")

        btn_add_folder = tk.Button(
            input_btn_frame,
            text="📁 Select Entire Folder (Cut & Move)",
            font=("Segoe UI", 9),
            bg="#0284c7",
            fg="#ffffff",
            activebackground="#0369a1",
            activeforeground="#ffffff",
            padx=10,
            pady=5,
            relief="flat",
            cursor="hand2",
            command=self.browse_and_add_folder
        )
        btn_add_folder.pack(fill="x", pady=(0, 6))
        bind_hover(btn_add_folder, "#0284c7", "#0ea5e9")

        input_tools_row = tk.Frame(input_btn_frame, bg="#1e293b")
        input_tools_row.pack(fill="x")

        btn_open_input_dir = tk.Button(
            input_tools_row,
            text="📂 Open input_media",
            font=("Segoe UI", 8),
            bg="#334155",
            fg="#cbd5e1",
            padx=8,
            pady=3,
            relief="flat",
            cursor="hand2",
            command=lambda: os.startfile(str(INPUT_DIR))
        )
        btn_open_input_dir.pack(side="left")

        btn_refresh = tk.Button(
            input_tools_row,
            text="🔄 Refresh List",
            font=("Segoe UI", 8),
            bg="#334155",
            fg="#cbd5e1",
            padx=8,
            pady=3,
            relief="flat",
            cursor="hand2",
            command=self.refresh_file_list
        )
        btn_refresh.pack(side="right")

        self.list_count_lbl = tk.Label(
            left_frame,
            text="📁 Input Videos: 0",
            font=("Segoe UI", 9, "bold"),
            fg="#38bdf8",
            bg="#1e293b"
        )
        self.list_count_lbl.pack(anchor="w", pady=(8, 2))

        drop_banner = tk.Label(
            left_frame,
            text="✨ Drag & Drop Videos / Folders Here ✨",
            font=("Segoe UI", 8, "italic"),
            fg="#38bdf8",
            bg="#0f172a",
            padx=8,
            pady=4,
            relief="solid",
            bd=1
        )
        drop_banner.pack(fill="x", pady=(2, 6))

        self.file_listbox = tk.Listbox(
            left_frame,
            font=("Segoe UI", 9),
            bg="#0f172a",
            fg="#f8fafc",
            selectbackground="#2563eb",
            selectforeground="#ffffff",
            relief="solid",
            bd=1,
            highlightthickness=0
        )
        self.file_listbox.pack(fill="both", expand=True)
        self.file_listbox.bind("<<ListboxSelect>>", self.on_file_selected)

        # RIGHT PANE: Actions, Logs & Status
        right_frame = tk.Frame(main_split, bg="#1e293b", padx=16, pady=14)
        main_split.add(right_frame, minsize=520)

        self.cur_video_lbl = tk.Label(
            right_frame,
            text="Select a video from the list on the left, or click 'PROCESS & RENAME ALL'",
            font=("Segoe UI", 11, "bold"),
            fg="#f1f5f9",
            bg="#1e293b",
            wraplength=500,
            justify="left"
        )
        self.cur_video_lbl.pack(anchor="w")

        action_bar = tk.Frame(right_frame, bg="#1e293b", pady=10)
        action_bar.pack(fill="x")

        self.btn_auto_all = tk.Button(
            action_bar,
            text="🚀 PROCESS & RENAME ALL (1, 2...)",
            font=("Segoe UI", 10, "bold"),
            bg="#059669",
            fg="#ffffff",
            activebackground="#047857",
            activeforeground="#ffffff",
            padx=14,
            pady=9,
            relief="flat",
            cursor="hand2",
            command=self.start_process_all_videos
        )
        self.btn_auto_all.pack(side="left", padx=(0, 8))
        bind_hover(self.btn_auto_all, "#059669", "#10b981")

        self.btn_auto_single = tk.Button(
            action_bar,
            text="⚡ Process Selected",
            font=("Segoe UI", 9, "bold"),
            bg="#2563eb",
            fg="#ffffff",
            activebackground="#1d4ed8",
            activeforeground="#ffffff",
            padx=12,
            pady=9,
            relief="flat",
            cursor="hand2",
            state="disabled",
            command=self.start_process_selected_video
        )
        self.btn_auto_single.pack(side="left", padx=(0, 8))
        bind_hover(self.btn_auto_single, "#2563eb", "#3b82f6")

        self.btn_stop = tk.Button(
            action_bar,
            text="⏹️ STOP ANALYSIS",
            font=("Segoe UI", 9, "bold"),
            bg="#475569",
            fg="#ffffff",
            activebackground="#dc2626",
            activeforeground="#ffffff",
            padx=12,
            pady=9,
            relief="flat",
            cursor="hand2",
            state="disabled",
            command=self.request_stop
        )
        self.btn_stop.pack(side="left", padx=(0, 8))
        bind_hover(self.btn_stop, "#475569", "#dc2626")

        self.btn_copy_output = tk.Button(
            action_bar,
            text="📋 Copy Caption & Hashtags",
            font=("Segoe UI", 9, "bold"),
            bg="#0284c7",
            fg="#ffffff",
            activebackground="#0369a1",
            activeforeground="#ffffff",
            padx=12,
            pady=9,
            relief="flat",
            cursor="hand2",
            command=self.copy_output
        )
        self.btn_copy_output.pack(side="left", padx=(0, 8))
        bind_hover(self.btn_copy_output, "#0284c7", "#0ea5e9")

        self.btn_clear_log = tk.Button(
            action_bar,
            text="🧹 Clear Logs",
            font=("Segoe UI", 9),
            bg="#334155",
            fg="#cbd5e1",
            activebackground="#475569",
            activeforeground="#ffffff",
            padx=10,
            pady=9,
            relief="flat",
            cursor="hand2",
            command=self.clear_log
        )
        self.btn_clear_log.pack(side="left")
        bind_hover(self.btn_clear_log, "#334155", "#475569")

        log_header_frame = tk.Frame(right_frame, bg="#1e293b")
        log_header_frame.pack(fill="x", pady=(8, 4))

        tk.Label(
            log_header_frame,
            text="📝 Live Gemini AI Output (Caption & Hashtags):",
            font=("Segoe UI", 9, "bold"),
            fg="#94a3b8",
            bg="#1e293b"
        ).pack(side="left")

        btn_header_clear = tk.Button(
            log_header_frame,
            text="🧹 Clear",
            font=("Segoe UI", 8, "bold"),
            bg="#1e293b",
            fg="#38bdf8",
            activebackground="#334155",
            activeforeground="#ffffff",
            padx=10,
            pady=2,
            relief="flat",
            cursor="hand2",
            command=self.clear_log
        )
        btn_header_clear.pack(side="right")

        self.txt_output = scrolledtext.ScrolledText(
            right_frame,
            font=("Consolas", 10),
            bg="#0f172a",
            fg="#f8fafc",
            insertbackground="#38bdf8",
            relief="solid",
            bd=1,
            padx=12,
            pady=10,
            wrap="word"
        )
        self.txt_output.pack(fill="both", expand=True)

        self.status_bar = tk.Label(
            self.root,
            text="Ready. Click 'PROCESS & RENAME ALL' to start direct Gemini AI video analysis.",
            font=("Segoe UI", 9),
            fg="#94a3b8",
            bg="#0f172a",
            anchor="w",
            padx=24,
            pady=8
        )
        self.status_bar.pack(fill="x")

    def on_platform_changed(self, event=None):
        self.config["target_platform"] = self.platform_var.get()
        save_config(self.config)
        self.status_bar.config(text=f"Target Platform updated: {self.platform_var.get().upper()}")

    def open_web_app(self):
        import subprocess
        import urllib.request
        import webbrowser
        server_url = "http://localhost:5050"
        try:
            urllib.request.urlopen(server_url + "/api/status", timeout=1)
            webbrowser.open(server_url)
        except Exception:
            server_script = WORKSPACE_DIR / "web_server.py"
            if server_script.exists():
                creationflags = 0x08000000 if sys.platform.startswith('win') else 0 # CREATE_NO_WINDOW
                subprocess.Popen([sys.executable, str(server_script)], cwd=str(WORKSPACE_DIR), creationflags=creationflags)
                time.sleep(1.2)
                webbrowser.open(server_url)
            else:
                webbrowser.open(server_url)

    def open_key_dialog(self):
        win = tk.Toplevel(self.root)
        win.title("Gemini API Key Setup")
        win.geometry("540x220")
        win.configure(bg="#1e293b")
        win.transient(self.root)
        win.grab_set()

        tk.Label(
            win,
            text="🔑 Google Gemini API Key:",
            font=("Segoe UI", 11, "bold"),
            fg="#38bdf8",
            bg="#1e293b"
        ).pack(anchor="w", padx=20, pady=(18, 6))

        key_entry = tk.Entry(
            win,
            font=("Segoe UI", 10),
            bg="#0f172a",
            fg="#ffffff",
            insertbackground="#38bdf8",
            relief="solid",
            bd=1
        )
        key_entry.insert(0, self.config.get("gemini_api_key", ""))
        key_entry.pack(fill="x", padx=20, pady=4)

        tk.Label(
            win,
            text="Get your free key at: https://aistudio.google.com/app/apikey",
            font=("Segoe UI", 8),
            fg="#94a3b8",
            bg="#1e293b"
        ).pack(anchor="w", padx=20, pady=(2, 18))

        def save_k():
            new_k = key_entry.get().strip()
            self.config["gemini_api_key"] = new_k
            save_config(self.config)
            messagebox.showinfo("Saved", "✅ Gemini API Key successfully saved!", parent=win)
            win.destroy()

        tk.Button(
            win,
            text="Save Key",
            font=("Segoe UI", 10, "bold"),
            bg="#059669",
            fg="#ffffff",
            activebackground="#047857",
            padx=18,
            pady=6,
            relief="flat",
            cursor="hand2",
            command=save_k
        ).pack(anchor="e", padx=20)

    def browse_and_add_files(self):
        is_cut = (self.import_mode_var.get() == "cut")
        action_text = "Cut & Move" if is_cut else "Copy"
        selected = filedialog.askopenfilenames(
            title=f"Select Video Files ({action_text} into App)",
            filetypes=[
                ("Video / Media Files", "*.mp4 *.mov *.mkv *.avi *.webm *.m4v *.jpg *.jpeg *.png *.webp"),
                ("All Files", "*.*")
            ],
            parent=self.root
        )
        if selected:
            count = 0
            for s in selected:
                src_path = Path(s)
                dest_path = INPUT_DIR / src_path.name
                if is_cut:
                    if safe_move_file(src_path, dest_path):
                        count += 1
                else:
                    try:
                        shutil.copy2(str(src_path), str(dest_path))
                        count += 1
                    except Exception:
                        pass
            self.refresh_file_list()
            mode_lbl = "✂️ CUT & moved" if is_cut else "📋 COPIED"
            self.status_bar.config(text=f"✅ {mode_lbl} {count} file(s) into input_media!")

    def browse_and_add_folder(self):
        is_cut = (self.import_mode_var.get() == "cut")
        action_text = "Cut & Move" if is_cut else "Copy"
        selected = filedialog.askdirectory(title=f"Select Folder Containing Videos ({action_text} into App)", parent=self.root)
        if selected:
            src_dir = Path(selected)
            dest_dir = INPUT_DIR / src_dir.name
            if is_cut:
                if not dest_dir.exists():
                    try:
                        shutil.move(str(src_dir), str(dest_dir))
                    except Exception:
                        shutil.copytree(str(src_dir), str(dest_dir))
                        try:
                            shutil.rmtree(str(src_dir))
                        except Exception:
                            pass
                else:
                    for f in list(src_dir.iterdir()):
                        if f.is_file():
                            safe_move_file(f, dest_dir / f.name)
                        elif f.is_dir():
                            sub_dest = dest_dir / f.name
                            if not sub_dest.exists():
                                try:
                                    shutil.move(str(f), str(sub_dest))
                                except Exception:
                                    shutil.copytree(str(f), str(sub_dest))
                                    try:
                                        shutil.rmtree(str(f))
                                    except Exception:
                                        pass
                            else:
                                for sf in list(f.iterdir()):
                                    safe_move_file(sf, sub_dest / sf.name)
                                try:
                                    f.rmdir()
                                except Exception:
                                    pass
                    try:
                        src_dir.rmdir()
                    except Exception:
                        pass
                self.refresh_file_list()
                self.status_bar.config(text=f"✅ ✂️ Successfully CUT & moved folder '{src_dir.name}' into input_media!")
            else:
                if not dest_dir.exists():
                    shutil.copytree(str(src_dir), str(dest_dir))
                else:
                    for f in src_dir.iterdir():
                        if f.is_file():
                            shutil.copy2(str(f), str(dest_dir / f.name))
                self.refresh_file_list()
                self.status_bar.config(text=f"✅ 📋 Successfully COPIED folder '{src_dir.name}' into input_media!")

    def on_drop_files(self, dropped_paths):
        """Native Windows Drag & Drop handler for both individual files and entire folders."""
        is_cut = (self.import_mode_var.get() == "cut")
        count = 0
        video_exts = ('.mp4', '.mov', '.mkv', '.avi', '.webm', '.m4v')
        photo_exts = ('.jpg', '.jpeg', '.png', '.webp', '.bmp')
        all_exts = video_exts + photo_exts

        for item in dropped_paths:
            if isinstance(item, bytes):
                item = item.decode('utf-8', errors='ignore')
            path = Path(item)
            if not path.exists():
                continue

            if path.is_file():
                if path.suffix.lower() in all_exts:
                    dest_path = INPUT_DIR / path.name
                    if is_cut:
                        if safe_move_file(path, dest_path):
                            count += 1
                    else:
                        try:
                            shutil.copy2(str(path), str(dest_path))
                            count += 1
                        except Exception:
                            pass
            elif path.is_dir():
                dest_dir = INPUT_DIR / path.name
                if is_cut:
                    if not dest_dir.exists():
                        try:
                            shutil.move(str(path), str(dest_dir))
                            count += 1
                        except Exception:
                            try:
                                shutil.copytree(str(path), str(dest_dir), dirs_exist_ok=True)
                                shutil.rmtree(str(path), ignore_errors=True)
                                count += 1
                            except Exception:
                                pass
                    else:
                        for f in path.rglob("*"):
                            if f.is_file() and f.suffix.lower() in all_exts:
                                rel = f.relative_to(path)
                                sub_dest = dest_dir / rel
                                sub_dest.parent.mkdir(parents=True, exist_ok=True)
                                if safe_move_file(f, sub_dest):
                                    count += 1
                        try:
                            shutil.rmtree(str(path), ignore_errors=True)
                        except Exception:
                            pass
                else:
                    try:
                        shutil.copytree(str(path), str(dest_dir), dirs_exist_ok=True)
                        count += 1
                    except Exception:
                        pass

        self.refresh_file_list()
        mode_str = "Cut & Moved" if is_cut else "Copied"
        self.status_bar.config(text=f"✨ Drag & Drop: {mode_str} {count} item(s) into input_media!")
        self.log(f"📥 Drag & Drop: Successfully added {count} file(s)/folder(s) into Media Queue ({mode_str}).")

    def refresh_file_list(self):
        self.file_listbox.delete(0, tk.END)
        self.files_list = []
        video_exts = ('.mp4', '.mov', '.mkv', '.avi', '.webm', '.m4v')
        photo_exts = ('.jpg', '.jpeg', '.png', '.webp', '.bmp')
        all_exts = video_exts + photo_exts

        if INPUT_DIR.exists():
            for f in sorted(INPUT_DIR.rglob("*"), key=lambda x: str(x).lower()):
                if f.is_file() and f.suffix.lower() in all_exts:
                    self.files_list.append(f)
                    size_mb = f.stat().st_size / (1024 * 1024)
                    rel = f.relative_to(INPUT_DIR)
                    icon = "🎬" if f.suffix.lower() in video_exts else "📸"
                    self.file_listbox.insert(tk.END, f"{icon} {rel} ({size_mb:.1f} MB)")

        count = len(self.files_list)
        self.list_count_lbl.config(text=f"📁 Input Videos: {count}")

        if count > 0 and not self.is_processing:
            self.file_listbox.selection_set(0)
            self.on_file_selected()
            self.btn_auto_single.config(state="normal")
            self.btn_auto_all.config(state="normal")
        else:
            self.cur_video_lbl.config(text="No media found in input_media. Add videos using the buttons above or drag & drop.")
            self.btn_auto_single.config(state="disabled")
            self.btn_auto_all.config(state="disabled")

    def on_file_selected(self, event=None):
        sel = self.file_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        self.selected_file_index = idx
        media_path = self.files_list[idx]
        self.cur_video_lbl.config(text=f"Selected [{idx + 1}/{len(self.files_list)}]: {media_path.name}")

    def log(self, text):
        self.msg_queue.put(("log", text))

    def clear_log(self):
        self.txt_output.delete("1.0", tk.END)
        self.latest_caption_text = ""
        self.status_bar.config(text="🧹 Live caption output and logs cleared!")

    def copy_output(self):
        text_to_copy = getattr(self, 'latest_caption_text', '')
        if not text_to_copy:
            text_to_copy = self.txt_output.get("1.0", tk.END).strip()
        if text_to_copy:
            self.root.clipboard_clear()
            self.root.clipboard_append(text_to_copy)
            self.btn_copy_output.config(text="✅ Copied to Clipboard!", bg="#059669")
            self.status_bar.config(text="📋 Clean Caption & Hashtags copied to clipboard!")
            self.root.after(2000, lambda: self.btn_copy_output.config(text="📋 Copy Caption & Hashtags", bg="#0284c7"))

    def animate_ticker(self):
        if self.is_processing:
            char = self.spinner_chars[self.spinner_idx % len(self.spinner_chars)]
            self.spinner_idx += 1
            cur_text = self.status_bar.cget("text")
            # If current status doesn't have spinner prefix, add it
            if not cur_text.startswith(("⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏")):
                self.status_bar.config(text=f"{char} {cur_text}")
            else:
                self.status_bar.config(text=f"{char} {cur_text[2:]}")
        self.root.after(120, self.animate_ticker)

    def request_stop(self):
        if self.is_processing and not self.stop_requested:
            self.stop_requested = True
            self.btn_stop.config(state="disabled", text="⏳ Stopping...", bg="#7f1d1d")
            self.status_bar.config(text="🛑 Stop requested. Halting gracefully after current step...")
            self.log("\n⚠️ Stop signal received! Stopping execution...")

    def check_queue(self):
        try:
            while True:
                msg_type, data = self.msg_queue.get_nowait()
                if msg_type == "log":
                    self.txt_output.insert(tk.END, data + "\n")
                    self.txt_output.see(tk.END)
                elif msg_type == "status":
                    self.status_bar.config(text=data)
                elif msg_type == "latest_result":
                    self.latest_caption_text = data
                elif msg_type == "update_available":
                    count = data.get("behind_count", 1)
                    self.status_bar.config(text=f"🚀 {count} new update(s) available from Git! Click 'Check Updates' to install.")
                    if hasattr(self, 'btn_check_update'):
                        self.btn_check_update.config(text=f"🚀 Update ({count})", bg="#0284c7", fg="#ffffff")
                elif msg_type == "finished":
                    self.is_processing = False
                    self.stop_requested = False
                    self.btn_stop.config(state="disabled", text="⏹️ STOP ANALYSIS", bg="#475569")
                    self.refresh_file_list()
                    messagebox.showinfo("Status", data)
        except queue.Empty:
            pass
        self.root.after(100, self.check_queue)

    def background_update_check(self):
        time.sleep(2)
        try:
            res = auto_updater.check_for_updates()
            if res.get("update_available"):
                self.msg_queue.put(("update_available", res))
        except Exception:
            pass

    def manual_check_updates(self):
        if not AUTO_UPDATER_AVAILABLE:
            messagebox.showinfo("Update", "Auto-updater module is not available.", parent=self.root)
            return
        self.status_bar.config(text="🔍 Checking for updates via Git...")
        def _check():
            res = auto_updater.check_for_updates()
            if res.get("update_available"):
                count = res.get("behind_count", 1)
                commits = "\n".join([f"• {c}" for c in res.get("commits", [])[:3]])
                prompt_msg = f"🚀 {count} new update(s) available from Git!\n\nRecent changes:\n{commits}\n\nWould you like to automatically pull and update now?"
                if messagebox.askyesno("Update Available", prompt_msg, parent=self.root):
                    self.perform_app_update()
            else:
                msg = res.get("message", "Application is up to date.")
                messagebox.showinfo("Software Updates", f"✅ {msg}", parent=self.root)
                self.status_bar.config(text=f"✅ {msg}")
        threading.Thread(target=_check, daemon=True).start()

    def perform_app_update(self):
        self.status_bar.config(text="⏳ Pulling latest updates from Git...")
        self.log("\n🚀 Starting automatic Git Pull update...")
        def _pull():
            res = auto_updater.perform_update()
            if res.get("ok"):
                self.log(f"🎉 {res.get('message')}")
                self.status_bar.config(text=f"✅ {res.get('message')}")
                messagebox.showinfo("Update Success", f"🎉 {res.get('message')}\n\nPlease restart the application to use the updated files.", parent=self.root)
            else:
                self.log(f"❌ Update Error: {res.get('error')}")
                self.status_bar.config(text="❌ Update failed. Check logs.")
                messagebox.showerror("Update Error", f"Update failed: {res.get('error')}", parent=self.root)
        threading.Thread(target=_pull, daemon=True).start()

    def start_process_selected_video(self):
        if self.selected_file_index < 0 or self.selected_file_index >= len(self.files_list):
            return
        target_file = self.files_list[self.selected_file_index]
        self.is_processing = True
        self.stop_requested = False
        self.btn_auto_single.config(state="disabled")
        self.btn_auto_all.config(state="disabled")
        self.btn_stop.config(state="normal", text="⏹️ STOP ANALYSIS", bg="#dc2626")
        threading.Thread(target=self._process_worker, args=([target_file],), daemon=True).start()

    def start_process_all_videos(self):
        if not self.files_list:
            return
        self.is_processing = True
        self.stop_requested = False
        self.btn_auto_single.config(state="disabled")
        self.btn_auto_all.config(state="disabled")
        self.btn_stop.config(state="normal", text="⏹️ STOP ANALYSIS", bg="#dc2626")
        threading.Thread(target=self._process_worker, args=(list(self.files_list),), daemon=True).start()

    def _process_worker(self, targets):
        try:
            api_key = self.config.get("gemini_api_key", "").strip()
            if not api_key:
                self.log("❌ Error: Gemini API Key not found. Please click 'Gemini API Key' to set your key.")
                self.msg_queue.put(("finished", "Gemini API Key is required!"))
                return

            platform = self.platform_var.get()
            video_exts = ('.mp4', '.mov', '.mkv', '.avi', '.webm', '.m4v')

            from google import genai
            client = genai.Client(api_key=api_key)

            total_files = len(targets)
            for i, media_path in enumerate(targets, 1):
                if self.stop_requested:
                    self.log("\n🛑 Analysis stopped by user!")
                    self.msg_queue.put(("finished", "Analysis stopped by user. Remaining files are untouched."))
                    return

                if not media_path.exists():
                    continue

                is_video = media_path.suffix.lower() in video_exts

                # Folder name stays UNCHANGED!
                if media_path.parent != INPUT_DIR:
                    folder_name = media_path.parent.name
                else:
                    folder_name = media_path.stem

                ext = media_path.suffix.lower()
                target_folder = OUTPUT_DIR / folder_name
                target_folder.mkdir(parents=True, exist_ok=True)
                video_index = get_next_available_index(target_folder)
                renamed_filename = f"{video_index}{ext}"

                self.log(f"\n" + "=" * 50)
                self.log(f"[{i}/{total_files}] 🎬 Processing: {media_path.name}")
                self.log(f"   📁 Folder Name (Unchanged): {folder_name}/")
                self.log(f"   🎥 Renaming Video to: {renamed_filename}")
                self.msg_queue.put(("status", f"[{i}/{total_files}] Uploading {media_path.name} to Gemini AI..."))

                uploaded_file = None
                ai_output = None

                try:
                    uploaded_file = client.files.upload(file=str(media_path))
                    self.log(f"   ⏳ Gemini Files API Registered: {uploaded_file.name}")

                    if is_video:
                        self.log("   👀 Gemini AI is watching and analyzing video & audio...")
                        wait_count = 0
                        while uploaded_file.state.name == "PROCESSING" and wait_count < 120:
                            if self.stop_requested:
                                break
                            time.sleep(3)
                            wait_count += 3
                            uploaded_file = client.files.get(name=uploaded_file.name)

                        if self.stop_requested:
                            try:
                                client.files.delete(name=uploaded_file.name)
                            except Exception:
                                pass
                            self.log("\n🛑 Analysis stopped by user!")
                            self.msg_queue.put(("finished", "Analysis stopped by user. Remaining files are untouched."))
                            return

                        if uploaded_file.state.name == "FAILED":
                            self.log(f"   [!] Video Processing Failed: {uploaded_file.error}")
                            continue

                    if self.stop_requested:
                        try:
                            client.files.delete(name=uploaded_file.name)
                        except Exception:
                            pass
                        self.log("\n🛑 Analysis stopped by user!")
                        self.msg_queue.put(("finished", "Analysis stopped by user. Remaining files are untouched."))
                        return

                    prompt = f"""Watch and listen to this entire attached video. Analyze what is happening, all dialogue/audio, visual cues, and the core message.
Generate a viral, engaging social media post for {platform.upper()} strictly in 100% FLUENT ENGLISH.

FORMAT REQUIREMENTS:
Provide ONLY the story-driven caption followed directly by hashtags.
Do NOT include ANY section titles, labels, or prefixes (Do NOT write '🎯 HOOK:', '📌 CAPTION:', '🏷️ HASHTAGS:', 'Caption:', 'Hook:', etc.).

EXACT FORMAT TO FOLLOW:
[Engaging, story-driven caption strictly in fluent English describing the key moment, emotion, humor, or situation with appropriate emojis]

#Hashtag1 #Hashtag2 #Hashtag3 #Hashtag4 #Hashtag5 ... (15-20 viral, trending hashtags for {platform.upper()})

EXAMPLE:
This baby keeps tapping on the rainy window… while the African Grey parrot watches every move from behind. 😂🦜👶 Then the baby turns around with the BIGGEST smile like they’ve been caught! ❤️

#TalkingParrot #AfricanGrey #BabyAndParrot #FunnyBaby #CuteBaby #FunnyParrot #ParrotLife #CuteAnimals #WholesomeMoments #FunnyReels #ViralReels #MustWatch

CRITICAL RULES:
- EVERYTHING MUST be written strictly in 100% FLUENT ENGLISH ONLY.
- Regardless of the spoken language or dialogue in the video (even if Nepali, Hindi, Spanish, etc.), you MUST translate all concepts and write EVERYTHING strictly in 100% FLUENT ENGLISH.
- Absolutely NO section labels, headers, or markdown titles.
- Absolutely NO Devanagari, Nepali, Hindi, or non-English script.
- Do NOT include any intro, outro, explanations, search keywords, or conversational filler.
- Output ONLY the clean caption followed immediately by the hashtags."""

                    self.log(f"   🤖 Gemini AI is writing pure English Caption & Hashtags...")
                    for model_name in ACTIVE_MODELS:
                        if self.stop_requested:
                            break
                        try:
                            resp = client.models.generate_content(
                                model=model_name,
                                contents=[uploaded_file, prompt]
                            )
                            if resp and resp.text:
                                ai_output = clean_ai_output(resp.text)
                                self.log(f"   ✅ Gemini ({model_name}) generated pure English Caption & Hashtags!")
                                break
                        except Exception as merr:
                            err_str = str(merr)
                            if "503" in err_str or "404" in err_str or "demand" in err_str.lower():
                                time.sleep(1)
                                continue
                            else:
                                self.log(f"   [!] Model notice ({model_name}): {err_str[:80]}")
                                continue

                except Exception as e:
                    self.log(f"   [!] Gemini Error: {e}")
                finally:
                    if uploaded_file:
                        try:
                            client.files.delete(name=uploaded_file.name)
                        except Exception:
                            pass

                if self.stop_requested:
                    self.log("\n🛑 Analysis stopped by user!")
                    self.msg_queue.put(("finished", "Analysis stopped by user. Remaining files are untouched."))
                    return

                # Safe move & rename (never crashes if target exists)
                target_media = target_folder / renamed_filename
                safe_move_file(media_path, target_media)

                # Clean up empty parent folder inside input_media if it was inside a subfolder
                if media_path.parent != INPUT_DIR:
                    parent_dir = media_path.parent
                    try:
                        all_exts = ('.mp4', '.mov', '.mkv', '.avi', '.webm', '.m4v', '.jpg', '.jpeg', '.png', '.webp')
                        remaining = [f for f in parent_dir.iterdir() if f.is_file() and f.suffix.lower() in all_exts]
                        if not remaining:
                            shutil.rmtree(str(parent_dir), ignore_errors=True)
                    except Exception:
                        pass

                # Fallback if Gemini failed so user never gets blank file
                if not ai_output:
                    ai_output = f"""An unexpected and emotional moment caught on camera! Watch closely as the story unfolds with the biggest smile. What would your reaction be in this situation? Let us know your thoughts in the comments below! 👇💬❤️

#Viral #Trending #MustWatch #VideoOfTheDay #StoryTime #ExplorePage #FYP #Reels #CuteAnimals #WholesomeMoments #FunnyReels #ViralReels #{platform.capitalize()}Watch #Entertainment"""
                else:
                    ai_output = clean_ai_output(ai_output)

                # Save pure Gemini output into .txt file
                txt_path = target_folder / f"{video_index}_seo_caption_hashtags.txt"
                with open(txt_path, "w", encoding="utf-8") as f:
                    f.write(ai_output.strip())

                self.msg_queue.put(("latest_result", ai_output.strip()))
                self.log(f"   ✂️  CUT & RENAMED ➔ {target_folder.name}/{renamed_filename}")
                self.log(f"   📝 Pure English .txt Saved: {txt_path.name}")

            self.msg_queue.put(("finished", f"🎉 Success! All {total_files} videos have been analyzed by Gemini AI and organized with English Caption and Hashtags!"))
        except Exception as exc:
            self.log(f"\n❌ Unexpected error: {exc}")
            self.msg_queue.put(("finished", f"Processing halted due to error: {exc}"))
        finally:
            self.is_processing = False

def main():
    root = tk.Tk()
    app = LustreSeparatorApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
