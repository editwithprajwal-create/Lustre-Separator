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
import subprocess
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
    BUNDLE_DIR = Path(getattr(sys, '_MEIPASS', Path(sys.executable).resolve().parent))
    WORKSPACE_DIR = Path(sys.executable).resolve().parent
else:
    BUNDLE_DIR = Path(__file__).resolve().parent
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
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-flash-latest",
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash",
    "gemini-3.8-flash"
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

def split_caption_and_hashtags(text):
    if not text:
        return "", ""
    hashtags = re.findall(r'#\w+', text)
    caption_part = re.sub(r'#\w+', '', text)
    caption_part = re.sub(r'[\r\n\t]+', ' ', caption_part)
    caption_part = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '', caption_part)
    caption_part = re.sub(r'\s+', ' ', caption_part).strip().rstrip('. ')
    hashtag_str = ' '.join(hashtags)
    return caption_part, hashtag_str

def generate_video_filename(ai_text, ext, target_folder=None, fallback_stem="video", max_len=240):
    ext = ext.lower() if ext else ".mp4"
    if not ext.startswith("."):
        ext = "." + ext

    caption, hashtags = split_caption_and_hashtags(ai_text)

    if not caption and not hashtags:
        base_name = fallback_stem
    elif not hashtags:
        base_name = caption
    elif not caption:
        base_name = hashtags
    else:
        candidate = f"{caption} {hashtags}"
        if len(candidate) <= max_len:
            base_name = candidate
        else:
            selected_tags = []
            tag_len = 0
            for tag in hashtags.split():
                if tag_len + len(tag) + 1 <= 85:
                    selected_tags.append(tag)
                    tag_len += len(tag) + 1
                else:
                    break
            tag_part = ' '.join(selected_tags)
            avail_for_caption = max_len - len(tag_part) - 1
            if len(caption) > avail_for_caption:
                truncated = caption[:avail_for_caption]
                last_space = truncated.rfind(' ')
                if last_space > avail_for_caption // 2:
                    caption_part = truncated[:last_space].rstrip('. ')
                else:
                    caption_part = truncated.rstrip('. ')
            else:
                caption_part = caption
            base_name = f"{caption_part} {tag_part}".strip()

    base_name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '', base_name).strip().rstrip('. ')
    if len(base_name) > max_len:
        base_name = base_name[:max_len].rstrip('. ')
    if not base_name:
        base_name = fallback_stem

    candidate_name = f"{base_name}{ext}"
    if target_folder is None:
        return candidate_name

    tf = Path(target_folder)
    if not tf.exists() or not (tf / candidate_name).exists():
        return candidate_name

    counter = 1
    while True:
        tag = f" ({counter})"
        trimmed_base = base_name[:(max_len - len(tag))].rstrip('. ')
        new_name = f"{trimmed_base}{tag}{ext}"
        if not (tf / new_name).exists():
            return new_name
        counter += 1

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

def open_directory_in_explorer(dir_path):
    """
    Instantly and reliably opens a directory in Windows Explorer.
    Uses non-blocking detached process with zero DDE hang.
    """
    try:
        p = Path(dir_path).resolve()
        p.mkdir(parents=True, exist_ok=True)
        path_str = str(p)

        def _do_open():
            try:
                subprocess.Popen(
                    ['explorer.exe', path_str],
                    close_fds=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL
                )
                return
            except Exception:
                pass
            try:
                subprocess.Popen(
                    ['cmd.exe', '/c', 'start', '', path_str],
                    close_fds=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL
                )
                return
            except Exception:
                pass
            try:
                os.startfile(path_str)
            except Exception:
                pass

        threading.Thread(target=_do_open, daemon=True).start()
        return True
    except Exception as e:
        print(f"Error opening directory {dir_path}: {e}")
        return False

def safe_move_file(src, dst, max_retries=6, delay=0.3):
    """
    Safely and STRICTLY moves (cuts) a file from src to dst.
    Guarantees src is completely removed from its source location (zero copying).
    Handles temporary file locks on Windows with retries and garbage collection.
    """
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

    import gc
    for attempt in range(max_retries):
        try:
            shutil.move(str(src), str(dst))
            if not src.exists():
                return True
        except Exception:
            gc.collect()
            time.sleep(delay)

    # Cross-volume or stubborn lock fallback:
    try:
        shutil.copy2(str(src), str(dst))
        if dst.exists() and dst.stat().st_size == src.stat().st_size:
            for attempt in range(max_retries):
                try:
                    gc.collect()
                    src.unlink()
                    return True
                except Exception:
                    time.sleep(delay)
            return True
    except Exception:
        pass

    return dst.exists() and dst.stat().st_size > 0

class LustreSeparatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("✨ Lustre Separator - AI Video SEO & Media Organizer")
        self.root.geometry("1120x780")
        self.root.minsize(960, 650)
        self.root.configure(bg="#060608")

        # Set Window Icon (uses iconbitmap + iconphoto for guaranteed Windows titlebar and taskbar rendering)
        for cand in [WORKSPACE_DIR / "assets" / "logo.ico", BUNDLE_DIR / "assets" / "logo.ico", WORKSPACE_DIR / "logo.ico"]:
            if cand.exists():
                try:
                    self.root.iconbitmap(str(cand))
                    break
                except Exception:
                    pass
        for cand in [WORKSPACE_DIR / "assets" / "logo.png", BUNDLE_DIR / "assets" / "logo.png", WORKSPACE_DIR / "logo.png"]:
            if cand.exists():
                try:
                    pil_ico = Image.open(str(cand)).resize((64, 64), Image.Resampling.LANCZOS)
                    self.taskbar_icon = ImageTk.PhotoImage(pil_ico)
                    self.root.iconphoto(True, self.taskbar_icon)
                    break
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

        self.done_count = 0
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
        threading.Thread(target=self.ensure_local_server, daemon=True).start()

    def ensure_local_server(self):
        import urllib.request
        try:
            with urllib.request.urlopen("http://127.0.0.1:5050/api/status", timeout=0.8) as res:
                if res.status == 200:
                    return
        except Exception:
            pass

        try:
            import web_server
            threading.Thread(target=lambda: web_server.run_server(port=5050, open_browser=False), daemon=True).start()
        except Exception as e:
            print(f"Error launching background web server: {e}")

    def setup_ui(self):
        # Header banner (Royal Smoked Obsidian with Brushed Gold Highlight)
        header = tk.Frame(self.root, bg="#0a0a0d", padx=20, pady=12, highlightthickness=1, highlightbackground="#221e14")
        header.pack(fill="x")

        # Load Logo in Header (Lustre Monogram Emblem)
        logo_png = None
        for cand in [WORKSPACE_DIR / "assets" / "logo.png", BUNDLE_DIR / "assets" / "logo.png", WORKSPACE_DIR / "logo.png", BUNDLE_DIR / "logo.png"]:
            if cand.exists():
                logo_png = cand
                break
        if logo_png:
            try:
                pil_img = Image.open(str(logo_png)).resize((44, 44), Image.Resampling.LANCZOS)
                self.logo_img = ImageTk.PhotoImage(pil_img)
                logo_lbl = tk.Label(header, image=self.logo_img, bg="#0a0a0d")
                logo_lbl.pack(side="left", padx=(0, 12))
            except Exception:
                pass

        header_text_frame = tk.Frame(header, bg="#0a0a0d")
        header_text_frame.pack(side="left", fill="both", expand=True)

        # Title Row: Brand + STUDIO PRO interactive hub
        title_row = tk.Frame(header_text_frame, bg="#0a0a0d")
        title_row.pack(anchor="w")

        title_lbl = tk.Label(
            title_row,
            text="✨ LUSTRE SEPARATOR",
            font=("Segoe UI", 15, "bold"),
            fg="#fce881",
            bg="#0a0a0d"
        )
        title_lbl.pack(side="left")

        # Studio Pro Hub Button (Imperial Gold Badge)
        self.btn_studio_pro = tk.Button(
            title_row,
            text="👑 STUDIO PRO • v2.5.0 ▾",
            font=("Segoe UI", 8, "bold"),
            bg="#2b2413",
            fg="#fce881",
            activebackground="#3d3319",
            activeforeground="#ffffff",
            padx=10,
            pady=3,
            relief="flat",
            cursor="hand2",
            command=self.open_studio_pro_dialog
        )
        self.btn_studio_pro.pack(side="left", padx=(10, 0))
        bind_hover(self.btn_studio_pro, "#2b2413", "#3d3319")

        subtitle_lbl = tk.Label(
            header_text_frame,
            text="Gemini Vision AI Engine • Sequential Media Renamer • Pure English SEO",
            font=("Segoe UI", 8),
            fg="#a3997e",
            bg="#0a0a0d"
        )
        subtitle_lbl.pack(anchor="w", pady=(2, 0))

        # Header Right Navigation (Live Engine + Folder links + Web Studio)
        header_actions = tk.Frame(header, bg="#0a0a0d")
        header_actions.pack(side="right")

        engine_pill = tk.Label(
            header_actions,
            text="✨ Gemini Vision: ONLINE",
            font=("Segoe UI", 8, "bold"),
            fg="#d4af37",
            bg="#16130d",
            padx=9,
            pady=4,
            relief="flat"
        )
        engine_pill.pack(side="left", padx=(0, 8))

        btn_open_in = tk.Button(
            header_actions,
            text="📂 Input",
            font=("Segoe UI", 8, "bold"),
            bg="#1a160f",
            fg="#fce881",
            activebackground="#2a2318",
            activeforeground="#ffffff",
            padx=10,
            pady=4,
            relief="flat",
            cursor="hand2",
            command=lambda: open_directory_in_explorer(INPUT_DIR)
        )
        btn_open_in.pack(side="left", padx=(0, 6))
        bind_hover(btn_open_in, "#1a160f", "#2a2318")

        btn_open_out = tk.Button(
            header_actions,
            text="📁 Output",
            font=("Segoe UI", 8, "bold"),
            bg="#1a160f",
            fg="#d4af37",
            activebackground="#2a2318",
            activeforeground="#ffffff",
            padx=10,
            pady=4,
            relief="flat",
            cursor="hand2",
            command=lambda: open_directory_in_explorer(OUTPUT_DIR)
        )
        btn_open_out.pack(side="left", padx=(0, 6))
        bind_hover(btn_open_out, "#1a160f", "#2a2318")

        btn_web_app = tk.Button(
            header_actions,
            text="🌐 Web Studio",
            font=("Segoe UI", 8, "bold"),
            bg="#d4af37",
            fg="#0b0904",
            activebackground="#ffd700",
            activeforeground="#0b0904",
            padx=12,
            pady=4,
            relief="flat",
            cursor="hand2",
            command=self.open_web_app
        )
        btn_web_app.pack(side="left")
        bind_hover(btn_web_app, "#d4af37", "#ffd700")

        # Top Control Bar (Target Destination Platform Chips + Mode + Queue & Done Counters)
        ctrl_bar = tk.Frame(self.root, bg="#0c0b08", padx=16, pady=8, highlightthickness=1, highlightbackground="#221e14")
        ctrl_bar.pack(fill="x")

        tk.Label(
            ctrl_bar,
            text="🎯 Destination:",
            font=("Segoe UI", 8, "bold"),
            fg="#fce881",
            bg="#0c0b08"
        ).pack(side="left", padx=(0, 6))

        self.platform_var = tk.StringVar(value=self.config.get("target_platform", "facebook"))
        self.platform_buttons = {}

        platforms = [
            ("facebook", "Facebook"),
            ("instagram", "Instagram Reels"),
            ("tiktok", "TikTok"),
            ("youtube", "YouTube Shorts")
        ]

        def select_platform(p_key):
            self.platform_var.set(p_key)
            self.on_platform_changed()
            self._update_platform_buttons()

        for p_key, p_label in platforms:
            btn_p = tk.Button(
                ctrl_bar,
                text=p_label,
                font=("Segoe UI", 8, "bold"),
                bg="#1a1710",
                fg="#a3997e",
                activebackground="#d4af37",
                activeforeground="#0b0904",
                padx=8,
                pady=2,
                relief="flat",
                cursor="hand2",
                command=lambda k=p_key: select_platform(k)
            )
            btn_p.pack(side="left", padx=(0, 4))
            self.platform_buttons[p_key] = btn_p

        self._update_platform_buttons()

        tk.Label(
            ctrl_bar,
            text="•  Mode:",
            font=("Segoe UI", 8, "bold"),
            fg="#a3997e",
            bg="#0c0b08"
        ).pack(side="left", padx=(8, 4))

        self.import_mode_var = tk.StringVar(value="cut")
        tk.Label(
            ctrl_bar,
            text="✂️ Direct Cut Mode",
            font=("Segoe UI", 8, "bold"),
            fg="#ffd700",
            bg="#18140c",
            padx=8,
            pady=2,
            relief="solid",
            bd=1
        ).pack(side="left", padx=(0, 10))

        self.direct_mode_var = tk.BooleanVar(value=False)
        self.cb_direct_mode = tk.Checkbutton(
            ctrl_bar,
            text="⚡ Direct Mode (No Move / No Save)",
            variable=self.direct_mode_var,
            font=("Segoe UI", 8, "bold"),
            fg="#ffd700",
            bg="#18140c",
            selectcolor="#0c0b08",
            activebackground="#2b2413",
            activeforeground="#ffffff",
            padx=8,
            pady=2,
            relief="solid",
            bd=1,
            cursor="hand2",
            command=self.on_direct_mode_toggle
        )
        self.cb_direct_mode.pack(side="left", padx=(6, 10))

        self.queue_stat_lbl = tk.Label(
            ctrl_bar,
            text="Queue: 0  •  Done: 0",
            font=("Segoe UI", 8, "bold"),
            fg="#d4af37",
            bg="#0c0b08"
        )
        self.queue_stat_lbl.pack(side="right")

        btn_reset_stat = tk.Button(
            ctrl_bar,
            text="🔄 Reset",
            font=("Segoe UI", 8, "bold"),
            bg="#1f1a10",
            fg="#ffd700",
            activebackground="#332a18",
            activeforeground="#ffffff",
            padx=7,
            pady=1,
            relief="solid",
            bd=1,
            cursor="hand2",
            command=self.full_reset_action
        )
        btn_reset_stat.pack(side="right", padx=(0, 8))
        bind_hover(btn_reset_stat, "#1f1a10", "#332a18")

        # Main Split Content
        main_split = tk.PanedWindow(self.root, orient="horizontal", bg="#060608", sashwidth=5)
        main_split.pack(fill="both", expand=True, padx=14, pady=6)

        # LEFT PANE: Input Media Queue & Drag/Drop
        left_frame = tk.Frame(main_split, bg="#0c0b0a", padx=12, pady=12, highlightthickness=1, highlightbackground="#221e14")
        main_split.add(left_frame, minsize=330)

        input_btn_frame = tk.Frame(left_frame, bg="#0c0b0a")
        input_btn_frame.pack(fill="x", pady=(0, 6))

        btn_add_files = tk.Button(
            input_btn_frame,
            text="✂️ Add Video Files",
            font=("Segoe UI", 9, "bold"),
            bg="#d4af37",
            fg="#0b0904",
            activebackground="#ffd700",
            activeforeground="#0b0904",
            padx=10,
            pady=5,
            relief="flat",
            cursor="hand2",
            command=self.browse_and_add_files
        )
        btn_add_files.pack(fill="x", pady=(0, 4))
        bind_hover(btn_add_files, "#d4af37", "#ffd700")

        btn_add_folder = tk.Button(
            input_btn_frame,
            text="📁 Add Folder",
            font=("Segoe UI", 8, "bold"),
            bg="#2b2413",
            fg="#fce881",
            activebackground="#3d3319",
            activeforeground="#ffffff",
            padx=10,
            pady=5,
            relief="flat",
            cursor="hand2",
            command=self.browse_and_add_folder
        )
        btn_add_folder.pack(fill="x", pady=(0, 6))
        bind_hover(btn_add_folder, "#2b2413", "#3d3319")

        # Drag & Drop Notice Banner
        drop_banner = tk.Label(
            left_frame,
            text="✨ Drag & Drop Videos / Folders Here ✨",
            font=("Segoe UI", 8, "italic"),
            fg="#ffd700",
            bg="#12100b",
            padx=8,
            pady=5,
            relief="solid",
            bd=1,
            highlightthickness=1,
            highlightbackground="#2b2413"
        )
        drop_banner.pack(fill="x", pady=(0, 6))

        self.list_count_lbl = tk.Label(
            left_frame,
            text="📁 Input Videos: 0",
            font=("Segoe UI", 8, "bold"),
            fg="#a3997e",
            bg="#0c0b0a"
        )
        self.list_count_lbl.pack(anchor="w", pady=(0, 4))

        self.file_listbox = tk.Listbox(
            left_frame,
            font=("Segoe UI", 9),
            bg="#080706",
            fg="#f8f6f0",
            selectbackground="#d4af37",
            selectforeground="#0b0904",
            relief="solid",
            bd=1,
            highlightthickness=0
        )
        self.file_listbox.pack(fill="both", expand=True)
        self.file_listbox.bind("<<ListboxSelect>>", self.on_file_selected)

        # Left bottom tools
        input_tools_row = tk.Frame(left_frame, bg="#0c0b0a")
        input_tools_row.pack(fill="x", pady=(6, 0))

        btn_open_input_dir = tk.Button(
            input_tools_row,
            text="📂 Open input_media",
            font=("Segoe UI", 8),
            bg="#1a160f",
            fg="#fce881",
            padx=8,
            pady=3,
            relief="flat",
            cursor="hand2",
            command=lambda: open_directory_in_explorer(INPUT_DIR)
        )
        btn_open_input_dir.pack(side="left")
        bind_hover(btn_open_input_dir, "#1a160f", "#2a2318")

        btn_delete_selected = tk.Button(
            input_tools_row,
            text="🗑️ Delete",
            font=("Segoe UI", 8, "bold"),
            bg="#2a1215",
            fg="#ff7b89",
            activebackground="#421a20",
            activeforeground="#ffffff",
            padx=8,
            pady=3,
            relief="solid",
            bd=1,
            cursor="hand2",
            command=self.delete_selected_file
        )
        btn_delete_selected.pack(side="left", padx=(6, 0))
        bind_hover(btn_delete_selected, "#2a1215", "#421a20")

        btn_refresh = tk.Button(
            input_tools_row,
            text="🔄 Refresh",
            font=("Segoe UI", 8),
            bg="#1a160f",
            fg="#fce881",
            padx=8,
            pady=3,
            relief="flat",
            cursor="hand2",
            command=self.refresh_file_list
        )
        btn_refresh.pack(side="right")
        bind_hover(btn_refresh, "#1a160f", "#2a2318")

        # RIGHT PANE: Actions, AI Social Media Package & Console Logs
        right_frame = tk.Frame(main_split, bg="#0c0b0a", padx=14, pady=12, highlightthickness=1, highlightbackground="#221e14")
        main_split.add(right_frame, minsize=540)

        # Selected video banner
        self.cur_video_lbl = tk.Label(
            right_frame,
            text="Select a video from the left, or click 'PROCESS & RENAME ALL'",
            font=("Segoe UI", 10, "bold"),
            fg="#f8f6f0",
            bg="#0c0b0a",
            wraplength=520,
            justify="left"
        )
        self.cur_video_lbl.pack(anchor="w", pady=(0, 8))

        # Main Process Actions Bar
        action_bar = tk.Frame(right_frame, bg="#0c0b0a")
        action_bar.pack(fill="x", pady=(0, 10))

        self.btn_auto_all = tk.Button(
            action_bar,
            text="⚡ PROCESS & RENAME ALL (1, 2...)",
            font=("Segoe UI", 10, "bold"),
            bg="#d4af37",
            fg="#0b0904",
            activebackground="#ffd700",
            activeforeground="#0b0904",
            padx=16,
            pady=8,
            relief="flat",
            cursor="hand2",
            command=self.start_process_all_videos
        )
        self.btn_auto_all.pack(side="left", padx=(0, 8))
        bind_hover(self.btn_auto_all, "#d4af37", "#ffd700")

        self.btn_auto_single = tk.Button(
            action_bar,
            text="▶ Process Selected",
            font=("Segoe UI", 9, "bold"),
            bg="#2b2413",
            fg="#fce881",
            activebackground="#3d3319",
            activeforeground="#ffffff",
            padx=12,
            pady=8,
            relief="flat",
            cursor="hand2",
            state="disabled",
            command=self.start_process_selected_video
        )
        self.btn_auto_single.pack(side="left", padx=(0, 8))
        bind_hover(self.btn_auto_single, "#2b2413", "#3d3319")

        self.btn_stop = tk.Button(
            action_bar,
            text="⏹ STOP",
            font=("Segoe UI", 9, "bold"),
            bg="#2d1717",
            fg="#fca5a5",
            activebackground="#dc2626",
            activeforeground="#ffffff",
            padx=12,
            pady=8,
            relief="flat",
            cursor="hand2",
            state="disabled",
            command=self.request_stop
        )
        self.btn_stop.pack(side="left")
        bind_hover(self.btn_stop, "#2d1717", "#dc2626")

        # Showcase Card: AI Social Media Package (Pure Story Caption & Hashtags)
        showcase_card = tk.Frame(right_frame, bg="#0e0d0a", padx=12, pady=10, highlightthickness=1, highlightbackground="#2b2413")
        showcase_card.pack(fill="both", expand=True, pady=(0, 8))

        showcase_header = tk.Frame(showcase_card, bg="#0e0d0a")
        showcase_header.pack(fill="x", pady=(0, 6))

        tk.Label(
            showcase_header,
            text="✨ AI Social Media Package (Story Caption & Hashtags):",
            font=("Segoe UI", 9, "bold"),
            fg="#fce881",
            bg="#0e0d0a"
        ).pack(side="left")

        self.lbl_caption_stats = tk.Label(
            showcase_header,
            text="0 chars • 0 words • 0 tags",
            font=("Segoe UI", 8),
            fg="#a3997e",
            bg="#0e0d0a"
        )
        self.lbl_caption_stats.pack(side="left", padx=(8, 0))

        # Compact action buttons (Clear & Copy All)
        self.btn_copy_output = tk.Button(
            showcase_header,
            text="📋 Copy All",
            font=("Segoe UI", 8, "bold"),
            bg="#d4af37",
            fg="#0b0904",
            activebackground="#ffd700",
            activeforeground="#0b0904",
            padx=10,
            pady=3,
            relief="flat",
            cursor="hand2",
            command=self.copy_output
        )
        self.btn_copy_output.pack(side="right")
        bind_hover(self.btn_copy_output, "#d4af37", "#ffd700")

        self.btn_clear_caption = tk.Button(
            showcase_header,
            text="🧹 Clear",
            font=("Segoe UI", 8),
            bg="#241818",
            fg="#fca5a5",
            activebackground="#ef4444",
            activeforeground="#ffffff",
            padx=8,
            pady=3,
            relief="flat",
            cursor="hand2",
            command=self.clear_caption
        )
        self.btn_clear_caption.pack(side="right", padx=(0, 6))
        bind_hover(self.btn_clear_caption, "#241818", "#3b2020")

        self.txt_caption = scrolledtext.ScrolledText(
            showcase_card,
            font=("Segoe UI", 10),
            bg="#060605",
            fg="#f8f6f0",
            insertbackground="#ffd700",
            relief="flat",
            padx=10,
            pady=8,
            wrap="word",
            height=9
        )
        self.txt_caption.pack(fill="both", expand=True)
        self.txt_caption.bind("<KeyRelease>", self.on_caption_edited)

        # Execution Logs Card
        log_card = tk.Frame(right_frame, bg="#080706", padx=10, pady=6, highlightthickness=1, highlightbackground="#221e14")
        log_card.pack(fill="x")

        log_top = tk.Frame(log_card, bg="#080706")
        log_top.pack(fill="x", pady=(0, 4))

        tk.Label(
            log_top,
            text="📟 Execution Console Logs:",
            font=("Segoe UI", 8, "bold"),
            fg="#fce881",
            bg="#080706"
        ).pack(side="left")

        self.btn_clear_log = tk.Button(
            log_top,
            text="🧹 Clear Log",
            font=("Segoe UI", 8),
            bg="#1a160f",
            fg="#a3997e",
            activebackground="#2a2318",
            activeforeground="#ffffff",
            padx=8,
            pady=1,
            relief="flat",
            cursor="hand2",
            command=self.clear_log
        )
        self.btn_clear_log.pack(side="right")
        bind_hover(self.btn_clear_log, "#1a160f", "#2a2318")

        self.txt_log = scrolledtext.ScrolledText(
            log_card,
            font=("Consolas", 9),
            bg="#040403",
            fg="#f3e5ab",
            insertbackground="#ffd700",
            relief="flat",
            padx=8,
            pady=6,
            wrap="word",
            height=5
        )
        self.txt_log.pack(fill="both", expand=True)

        self.status_bar = tk.Label(
            self.root,
            text="Ready. Click 'PROCESS & RENAME ALL' to start direct Gemini AI video analysis.",
            font=("Segoe UI", 9),
            fg="#a3997e",
            bg="#0a0a0d",
            anchor="w",
            padx=20,
            pady=6
        )
        self.status_bar.pack(fill="x")

    def _update_platform_buttons(self):
        cur = self.platform_var.get()
        for p_key, btn in getattr(self, 'platform_buttons', {}).items():
            if p_key == cur:
                btn.config(bg="#d4af37", fg="#0b0904")
                bind_hover(btn, "#d4af37", "#ffd700")
            else:
                btn.config(bg="#1a1710", fg="#a3997e")
                bind_hover(btn, "#1a1710", "#2b261b")

    def on_platform_changed(self, event=None):
        self.config["target_platform"] = self.platform_var.get()
        save_config(self.config)
        self._update_platform_buttons()
        self.status_bar.config(text=f"Target Platform updated: {self.platform_var.get().upper()}")

    def open_web_app(self):
        import urllib.request
        import webbrowser
        server_url = "http://localhost:5050"

        # Check if already alive
        alive = False
        try:
            with urllib.request.urlopen("http://127.0.0.1:5050/api/status", timeout=0.8) as res:
                if res.status == 200:
                    alive = True
        except Exception:
            pass

        if not alive:
            try:
                import web_server
                threading.Thread(target=lambda: web_server.run_server(port=5050, open_browser=False), daemon=True).start()
                for _ in range(15):
                    time.sleep(0.2)
                    try:
                        with urllib.request.urlopen("http://127.0.0.1:5050/api/status", timeout=0.5) as res:
                            if res.status == 200:
                                alive = True
                                break
                    except Exception:
                        pass
            except Exception as e:
                print(f"Error starting web server: {e}")

        webbrowser.open(server_url)

    def open_key_dialog(self):
        self.open_studio_pro_dialog()

    def open_studio_pro_dialog(self):
        win = tk.Toplevel(self.root)
        win.title("✨ STUDIO PRO Center - API Key & Updates")
        win.geometry("560x440")
        win.configure(bg="#0c0b08")
        win.transient(self.root)
        win.grab_set()

        # Modal Header
        top_frame = tk.Frame(win, bg="#0f0e0b", padx=20, pady=14, highlightthickness=1, highlightbackground="#221e14")
        top_frame.pack(fill="x")

        tk.Label(
            top_frame,
            text="✨ STUDIO PRO SUITE",
            font=("Segoe UI", 13, "bold"),
            fg="#fce881",
            bg="#0f0e0b"
        ).pack(anchor="w")

        local_ver = auto_updater.get_local_version() if AUTO_UPDATER_AVAILABLE else {"version": "2.5.0"}
        cur_v = local_ver.get("version", "2.5.0")

        self.dlg_ver_lbl = tk.Label(
            top_frame,
            text=f"Version {cur_v} (Stable)  •  Gemini Vision Engine  •  Git Auto-Updater",
            font=("Segoe UI", 9),
            fg="#a3997e",
            bg="#0f0e0b"
        )
        self.dlg_ver_lbl.pack(anchor="w", pady=(2, 0))

        content_box = tk.Frame(win, bg="#0c0b08", padx=20, pady=14)
        content_box.pack(fill="both", expand=True)

        # CARD 1: Gemini API Key
        key_card = tk.Frame(content_box, bg="#14120e", padx=14, pady=12, highlightthickness=1, highlightbackground="#2b2413")
        key_card.pack(fill="x", pady=(0, 12))

        tk.Label(
            key_card,
            text="🔑 Google Gemini API Key:",
            font=("Segoe UI", 10, "bold"),
            fg="#fce881",
            bg="#14120e"
        ).pack(anchor="w", pady=(0, 4))

        key_row = tk.Frame(key_card, bg="#14120e")
        key_row.pack(fill="x", pady=(0, 6))

        key_entry = tk.Entry(
            key_row,
            font=("Segoe UI", 9),
            bg="#080706",
            fg="#ffffff",
            insertbackground="#ffd700",
            relief="solid",
            bd=1
        )
        key_entry.insert(0, self.config.get("gemini_api_key", ""))
        key_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        def _save_key():
            k = key_entry.get().strip()
            self.config["gemini_api_key"] = k
            save_config(self.config)
            messagebox.showinfo("Saved", "✅ Gemini API Key saved successfully!", parent=win)

        btn_save = tk.Button(
            key_row,
            text="💾 Save Key",
            font=("Segoe UI", 8, "bold"),
            bg="#d4af37",
            fg="#0b0904",
            activebackground="#ffd700",
            activeforeground="#0b0904",
            padx=10,
            pady=3,
            relief="flat",
            cursor="hand2",
            command=_save_key
        )
        btn_save.pack(side="right")
        bind_hover(btn_save, "#d4af37", "#ffd700")

        tk.Label(
            key_card,
            text="Get a free key from Google: https://aistudio.google.com/app/apikey",
            font=("Segoe UI", 8),
            fg="#a3997e",
            bg="#14120e"
        ).pack(anchor="w")

        # CARD 2: Auto-Updater
        up_card = tk.Frame(content_box, bg="#14120e", padx=14, pady=12, highlightthickness=1, highlightbackground="#2b2413")
        up_card.pack(fill="x")

        up_title_row = tk.Frame(up_card, bg="#14120e")
        up_title_row.pack(fill="x", pady=(0, 4))

        tk.Label(
            up_title_row,
            text="🚀 Automatic Application Updates (Git Pull):",
            font=("Segoe UI", 10, "bold"),
            fg="#fce881",
            bg="#14120e"
        ).pack(side="left")

        git_info = auto_updater.get_git_info() if AUTO_UPDATER_AVAILABLE else {}
        branch_name = git_info.get("branch", "main")
        commit_hash = git_info.get("commit", "")[:7]

        status_txt = f"Installed Build: v{cur_v}"
        if commit_hash and commit_hash != "none":
            status_txt += f" ({branch_name}@{commit_hash})"

        lbl_up_status = tk.Label(
            up_card,
            text=status_txt,
            font=("Segoe UI", 8),
            fg="#a3997e",
            bg="#14120e"
        )
        lbl_up_status.pack(anchor="w", pady=(0, 8))

        up_btns = tk.Frame(up_card, bg="#14120e")
        up_btns.pack(fill="x")

        def _check_and_refresh():
            lbl_up_status.config(text="🔍 Checking remote Git origin for new commits...", fg="#fce881")
            win.update_idletasks()
            res = auto_updater.check_for_updates() if AUTO_UPDATER_AVAILABLE else {}
            if res.get("update_available"):
                c = res.get("behind_count", 1)
                lbl_up_status.config(text=f"🚀 {c} new update(s) available to pull!", fg="#ffd700")
                btn_up_now.config(state="normal", text=f"🚀 Update Now ({c} commits)", bg="#d4af37", fg="#0b0904")
                self.btn_studio_pro.config(text=f"👑 STUDIO PRO • Update ({c}) ▾", bg="#d4af37", fg="#0b0904")
            else:
                lbl_up_status.config(text=f"✅ {res.get('message', 'Application is completely up to date.')}", fg="#10b981")
                btn_up_now.config(state="disabled", text="🚀 Up to date", bg="#26221b", fg="#666666")
                self.btn_studio_pro.config(text=f"👑 STUDIO PRO • v{cur_v} ▾", bg="#2b2413", fg="#fce881")

        def _do_update():
            if messagebox.askyesno("Confirm Update", "Do you want to run Git Pull now?\nYour config.json (API Key) and media folders will be safely preserved.", parent=win):
                lbl_up_status.config(text="⏳ Pulling updates from Git...", fg="#fce881")
                win.update_idletasks()
                res = auto_updater.perform_update() if AUTO_UPDATER_AVAILABLE else {"ok": False, "error": "Updater unavailable"}
                if res.get("ok"):
                    messagebox.showinfo("Update Complete", f"🎉 {res.get('message')}\n\nPlease close and reopen Lustre Separator to apply all changes!", parent=win)
                    win.destroy()
                else:
                    messagebox.showerror("Update Failed", f"Update error: {res.get('error')}", parent=win)

        btn_chk = tk.Button(
            up_btns,
            text="🔄 Check for Updates",
            font=("Segoe UI", 8, "bold"),
            bg="#2b2413",
            fg="#fce881",
            activebackground="#3d3319",
            activeforeground="#ffffff",
            padx=12,
            pady=5,
            relief="flat",
            cursor="hand2",
            command=_check_and_refresh
        )
        btn_chk.pack(side="left", padx=(0, 8))
        bind_hover(btn_chk, "#2b2413", "#3d3319")

        btn_up_now = tk.Button(
            up_btns,
            text="🚀 Update Now (Git Pull)",
            font=("Segoe UI", 8, "bold"),
            bg="#26221b",
            fg="#666666",
            activebackground="#ffd700",
            activeforeground="#0b0904",
            padx=14,
            pady=5,
            relief="flat",
            cursor="hand2",
            state="disabled",
            command=_do_update
        )
        btn_up_now.pack(side="left")
        bind_hover(btn_up_now, "#26221b", "#d4af37")

        # Bottom Close button
        btn_close = tk.Button(
            win,
            text="Close",
            font=("Segoe UI", 8),
            bg="#1a160f",
            fg="#a3997e",
            activebackground="#2a2318",
            activeforeground="#ffffff",
            padx=16,
            pady=4,
            relief="flat",
            cursor="hand2",
            command=win.destroy
        )
        btn_close.pack(side="bottom", pady=(0, 14))
        bind_hover(btn_close, "#1a160f", "#2a2318")

    def browse_and_add_files(self):
        selected = filedialog.askopenfilenames(
            title="Select Video Files (Direct CUT into input_media)",
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
                if safe_move_file(src_path, dest_path):
                    count += 1
            self.refresh_file_list()
            self.status_bar.config(text=f"✅ ✂️ Successfully CUT {count} file(s) into input_media!")

    def browse_and_add_folder(self):
        selected = filedialog.askdirectory(title="Select Folder Containing Videos (Direct CUT into input_media)", parent=self.root)
        if selected:
            src_dir = Path(selected)
            dest_dir = INPUT_DIR / src_dir.name
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

    def on_drop_files(self, dropped_paths):
        """Native Windows Drag & Drop handler for both individual files and entire folders."""
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
                    if safe_move_file(path, dest_path):
                        count += 1
            elif path.is_dir():
                dest_dir = INPUT_DIR / path.name
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

        self.refresh_file_list()
        self.status_bar.config(text=f"✨ Drag & Drop: CUT {count} item(s) into input_media!")
        self.log(f"📥 Drag & Drop: Successfully CUT {count} file(s)/folder(s) into Media Queue.")

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
        if hasattr(self, 'queue_stat_lbl'):
            self.queue_stat_lbl.config(text=f"Queue: {count}  •  Done: {self.done_count}")

        if count > 0 and not self.is_processing:
            self.file_listbox.selection_set(0)
            self.on_file_selected()
            self.btn_auto_single.config(state="normal")
            self.btn_auto_all.config(state="normal")
        else:
            self.cur_video_lbl.config(text="No media found in input_media. Add videos using the buttons above or drag & drop.")
            self.btn_auto_single.config(state="disabled")
            self.btn_auto_all.config(state="disabled")

    def delete_selected_file(self):
        sel = self.file_listbox.curselection()
        if not sel or not self.files_list:
            messagebox.showinfo("No Selection", "Please select a video file from the list to delete.", parent=self.root)
            return
        idx = sel[0]
        if idx >= len(self.files_list):
            return
        target_path = self.files_list[idx]
        confirm = messagebox.askyesno(
            "Confirm Delete",
            f"Are you sure you want to permanently delete:\n\n'{target_path.name}'\n\nfrom input_media?",
            parent=self.root
        )
        if confirm:
            try:
                target_path.unlink()
                try:
                    if target_path.parent != INPUT_DIR and not any(target_path.parent.iterdir()):
                        target_path.parent.rmdir()
                except Exception:
                    pass
                self.log(f"🗑️ Deleted input file: {target_path.name}")
                self.status_bar.config(text=f"🗑️ Deleted: {target_path.name}")
                self.refresh_file_list()
            except Exception as e:
                messagebox.showerror("Delete Error", f"Failed to delete file:\n{e}", parent=self.root)

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
        try:
            import web_server
            web_server.state.add_log(text)
        except Exception:
            pass

    def clear_log(self):
        if hasattr(self, 'txt_log'):
            self.txt_log.delete("1.0", tk.END)
        self.status_bar.config(text="🧹 Execution logs cleared!")
        try:
            import web_server
            web_server.state.clear_logs()
        except Exception:
            pass

    def clear_caption(self):
        if hasattr(self, 'txt_caption'):
            self.txt_caption.delete("1.0", tk.END)
        self.latest_caption_text = ""
        self.done_count = 0
        if hasattr(self, 'queue_stat_lbl'):
            self.queue_stat_lbl.config(text=f"Queue: {len(self.files_list)}  •  Done: 0")
        if hasattr(self, 'lbl_caption_stats'):
            self.lbl_caption_stats.config(text="0 chars • 0 words • 0 tags")
        self.status_bar.config(text="🧹 Caption, hashtags & Done counter cleared!")

    def full_reset_action(self):
        self.done_count = 0
        self.clear_caption()
        self.refresh_file_list()
        self.status_bar.config(text="🔄 Studio Fully Refreshed: Done counter & output reset to 0!")

    def update_caption_stats(self, text):
        if hasattr(self, 'lbl_caption_stats'):
            cleaned = text.strip() if text else ""
            chars = len(cleaned)
            words = len(cleaned.split()) if cleaned else 0
            tags = len(re.findall(r'#[\w\u0080-\uFFFF]+', cleaned))
            self.lbl_caption_stats.config(text=f"{chars} chars • {words} words • {tags} tags")

    def on_caption_edited(self, event=None):
        if hasattr(self, 'txt_caption'):
            t = self.txt_caption.get("1.0", tk.END).strip()
            self.update_caption_stats(t)

    def copy_output(self):
        text_to_copy = ""
        if hasattr(self, 'txt_caption'):
            text_to_copy = self.txt_caption.get("1.0", tk.END).strip()
        if not text_to_copy:
            text_to_copy = getattr(self, 'latest_caption_text', '')
        if text_to_copy:
            self.root.clipboard_clear()
            self.root.clipboard_append(text_to_copy)
            self.btn_copy_output.config(text="✅ Copied!", bg="#10b981")
            self.status_bar.config(text="📋 Clean Caption & Hashtags copied to clipboard!")
            self.root.after(2000, lambda: self.btn_copy_output.config(text="📋 Copy All", bg="#d4af37"))

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
                    if hasattr(self, 'txt_log'):
                        self.txt_log.insert(tk.END, data + "\n")
                        self.txt_log.see(tk.END)
                elif msg_type == "status":
                    self.status_bar.config(text=data)
                elif msg_type == "latest_result":
                    self.latest_caption_text = data
                    if hasattr(self, 'txt_caption'):
                        self.txt_caption.delete("1.0", tk.END)
                        self.txt_caption.insert("1.0", data)
                    self.update_caption_stats(data)
                elif msg_type == "update_available":
                    count = data.get("behind_count", 1)
                    self.status_bar.config(text=f"🚀 {count} new update(s) available! Click 'STUDIO PRO' to install.")
                    if hasattr(self, 'btn_studio_pro'):
                        self.btn_studio_pro.config(text=f"👑 STUDIO PRO • Update ({count}) ▾", bg="#d4af37", fg="#0b0904")
                elif msg_type == "done_count":
                    if hasattr(self, 'queue_stat_lbl'):
                        self.queue_stat_lbl.config(text=f"Queue: {len(self.files_list)}  •  Done: {data}")
                elif msg_type == "finished":
                    self.is_processing = False
                    self.stop_requested = False
                    self.btn_stop.config(state="disabled", text="⏹ STOP", bg="#2d1717")
                    self.refresh_file_list()
                    messagebox.showinfo("Status", data)
        except queue.Empty:
            pass

        # Live Web Studio state sync
        try:
            import web_server
            ws_state = getattr(web_server, 'state', None)
            if ws_state:
                if not self.is_processing and ws_state.is_processing:
                    self.status_bar.config(text=f"🌐 Web Studio: [{ws_state.progress_current}/{ws_state.progress_total}] {ws_state.current_file}")
                    if ws_state.latest_result and getattr(self, 'latest_caption_text', '') != ws_state.latest_result:
                        self.latest_caption_text = ws_state.latest_result
                        if hasattr(self, 'txt_caption'):
                            self.txt_caption.delete("1.0", tk.END)
                            self.txt_caption.insert("1.0", ws_state.latest_result)
                        self.update_caption_stats(ws_state.latest_result)
                elif self.is_processing and ws_state.stop_requested:
                    self.stop_requested = True
        except Exception:
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
            try:
                import web_server
                web_server.state.is_processing = True
                web_server.state.stop_requested = False
                web_server.state.progress_total = total_files
            except Exception:
                pass

            for i, media_path in enumerate(targets, 1):
                try:
                    import web_server
                    web_server.state.current_file = media_path.name
                    web_server.state.progress_current = i
                    if web_server.state.stop_requested:
                        self.stop_requested = True
                except Exception:
                    pass

                if self.stop_requested:
                    self.log("\n🛑 Analysis stopped by user!")
                    self.msg_queue.put(("finished", "Analysis stopped by user. Remaining files are untouched."))
                    return

                if not media_path.exists():
                    continue

                is_video = media_path.suffix.lower() in video_exts
                is_direct = self.direct_mode_var.get()

                if is_direct:
                    target_folder = None
                    renamed_filename = media_path.name
                    self.log(f"\n" + "=" * 50)
                    self.log(f"[{i}/{total_files}] ⚡ Direct Extract: {media_path.name}")
                    self.log("   🛡️ Zero Modifications: Original file will NOT be moved, cut, copied, or renamed.")
                    self.log("   🛡️ Zero Disk Writes: No output folders or .txt files created on disk.")
                    self.msg_queue.put(("status", f"[{i}/{total_files}] ⚡ Direct AI Scan: {media_path.name}..."))
                else:
                    # Folder name stays UNCHANGED!
                    if media_path.parent != INPUT_DIR:
                        folder_name = media_path.parent.name
                    else:
                        folder_name = media_path.stem

                    ext = media_path.suffix.lower()
                    target_folder = OUTPUT_DIR / folder_name
                    target_folder.mkdir(parents=True, exist_ok=True)

                    self.log(f"\n" + "=" * 50)
                    self.log(f"[{i}/{total_files}] 🎬 Processing: {media_path.name}")
                    self.log(f"   📁 Folder Name (Unchanged): {folder_name}/")
                    self.log("   🎥 Video will be renamed with Caption & Hashtags")
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
She walks into the house with her suitcase and paperwork… and within seconds the entire family confrontation explodes. 😳📄💔 Accusations fly, everyone gets pulled into the argument, and by the end one person is left standing there as the others walk away. Family drama just got REAL. 👀🔥

#FamilyDrama #FamilyConflict #FamilySecrets #RelationshipDrama #EmotionalStory #FamilyChaos #DramaReels #UnexpectedTruth #StoryTime #EmotionalDrama #ViralReels #MustWatch

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
                    uploaded_file = None
                    import gc
                    gc.collect()
                    time.sleep(0.2)

                if self.stop_requested:
                    self.log("\n🛑 Analysis stopped by user!")
                    self.msg_queue.put(("finished", "Analysis stopped by user. Remaining files are untouched."))
                    return

                if is_direct:
                    self.msg_queue.put(("latest_result", ai_output.strip()))
                    self.log(f"   ✨ Direct Extract Complete: '{media_path.name}' remains 100% untouched.")
                    self.done_count += 1
                    self.msg_queue.put(("done_count", self.done_count))
                else:
                    # Generate video filename directly from AI Caption + Hashtags (zero .txt file)
                    renamed_filename = generate_video_filename(ai_output, ext, target_folder, fallback_stem=media_path.stem)
                    target_media = target_folder / renamed_filename

                    # Strictly CUT & Move media from input_media to output_media
                    safe_move_file(media_path, target_media)
                    if media_path.exists():
                        try:
                            import gc
                            gc.collect()
                            media_path.unlink()
                        except Exception:
                            pass

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

                    self.msg_queue.put(("latest_result", ai_output.strip()))
                    try:
                        import web_server
                        web_server.state.latest_result = {
                            "folder": target_folder.name,
                            "video_file": renamed_filename,
                            "txt_file": "",
                            "content": ai_output
                        }
                    except Exception:
                        pass
                    self.log(f"   ✂️  CUT & RENAMED ➔ {target_folder.name}/{renamed_filename}")
                    self.done_count += 1
                    self.msg_queue.put(("done_count", self.done_count))

            self.msg_queue.put(("finished", f"🎉 Success! All {total_files} videos have been analyzed by Gemini AI and organized with English Caption and Hashtags!"))
        except Exception as exc:
            self.log(f"\n❌ Unexpected error: {exc}")
            self.msg_queue.put(("finished", f"Processing halted due to error: {exc}"))
        finally:
            self.is_processing = False
            try:
                import web_server
                web_server.state.is_processing = False
            except Exception:
                pass

    def on_direct_mode_toggle(self):
        is_direct = self.direct_mode_var.get()
        if is_direct:
            self.btn_auto_all.config(text="⚡ DIRECT EXTRACT ALL")
            self.btn_auto_single.config(text="⚡ Direct Extract Selected")
            self.status_bar.config(text="⚡ Direct Mode ON: Videos remain 100% untouched. No files will be moved, cut, or saved.")
            self.log("\n⚡ [Direct Extract Mode] ON: Original files stay untouched (0 moves / 0 cuts / 0 saves).")
        else:
            self.btn_auto_all.config(text="⚡ PROCESS & RENAME ALL")
            self.btn_auto_single.config(text="▶ Process Selected")
            self.status_bar.config(text="📁 Standard Mode ON: Videos will be organized & renamed into output_media.")
            self.log("\n📁 [Standard Mode] ON: Videos will be moved & renamed into sequential numbered folders.")

def is_server_alive(port=5050):
    try:
        import urllib.request
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/status", timeout=0.8) as resp:
            return resp.status == 200
    except Exception:
        return False

def start_embedded_server(port=5050):
    if is_server_alive(port):
        return True
    try:
        import web_server
        server_thread = threading.Thread(
            target=lambda: web_server.run_server(port=port, open_browser=False),
            daemon=True
        )
        server_thread.start()
        for _ in range(40):
            if is_server_alive(port):
                return True
            time.sleep(0.1)
    except Exception as e:
        print(f"Error starting embedded web server: {e}")
    return is_server_alive(port)

def find_browser_app_executable():
    possible_paths = [
        # Microsoft Edge (standard on Windows 10 & 11)
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe"),
        # Google Chrome
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe"),
        # Brave / other Chromium
        os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe"),
        r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
    ]
    for p in possible_paths:
        if p and os.path.isfile(p):
            return p
    return None

def launch_modern_desktop_app():
    """Launches the modern, animated Web Studio in a native desktop app window."""
    app_url = "http://localhost:5050"
    browser_exe = find_browser_app_executable()

    def _open_ui():
        time.sleep(1.0)
        if browser_exe:
            profile_dir = Path(os.path.expandvars(r"%LOCALAPPDATA%\LustreSeparator\Profile"))
            profile_dir.mkdir(parents=True, exist_ok=True)
            cmd = [
                browser_exe,
                f"--app={app_url}",
                "--window-size=1280,860",
                f"--user-data-dir={profile_dir}",
                "--disable-default-apps",
                "--disable-extensions",
                "--no-first-run",
                "--no-default-browser-check"
            ]
            try:
                subprocess.Popen(cmd)
                return
            except Exception as e:
                print(f"Browser launch notice: {e}")

        # Fallback to pywebview if available
        try:
            import webview
            w = webview.create_window(
                "✨ Lustre Separator - AI Video SEO & Media Organizer",
                app_url,
                width=1280,
                height=860,
                min_size=(960, 600)
            )
            webview.start()
            return
        except Exception:
            pass

        # Fallback to default browser
        import webbrowser
        webbrowser.open(app_url)

    if not is_server_alive(5050):
        threading.Thread(target=_open_ui, daemon=True).start()
        import web_server
        web_server.run_server(port=5050, open_browser=False)
    else:
        _open_ui()
        while is_server_alive(5050):
            time.sleep(1)

def main():
    if "--web" in sys.argv:
        launch_modern_desktop_app()
    else:
        root = tk.Tk()
        app = LustreSeparatorApp(root)
        root.mainloop()

if __name__ == "__main__":
    main()
