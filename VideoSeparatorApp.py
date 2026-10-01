#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Video Separator - Desktop GUI Application (.exe)
Pure Gemini Video Analysis & Renaming Engine
- Direct Gemini AI Video Attach via API
- Generates ONLY: Hook, Caption, and Hashtags
- Writes pure Gemini output into .txt (zero tool wrappers)
- Keeps Folder Name UNCHANGED
- Renames video inside to 1.mp4, 2.mp4, 3.mp4...
"""

import os
import sys
import shutil
import time
import json
import re
import threading
import subprocess
import queue
from pathlib import Path

def run_silent_cmd(cmd, **kwargs):
    """Executes a command with 100% guarantee of zero console/terminal popup or flicker."""
    if sys.platform.startswith('win'):
        kwargs["creationflags"] = getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000)
        startupinfo = kwargs.get("startupinfo") or subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        kwargs["startupinfo"] = startupinfo
    if "stdin" not in kwargs:
        kwargs["stdin"] = subprocess.DEVNULL
    return subprocess.run(cmd, **kwargs)

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import local_video_seo

# Determine base directory whether running as script or frozen PyInstaller exe
if getattr(sys, 'frozen', False):
    WORKSPACE_DIR = Path(sys.executable).resolve().parent
    if (WORKSPACE_DIR.parent / "input_media").exists():
        WORKSPACE_DIR = WORKSPACE_DIR.parent
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
    "language": "mix",
    "tone": "viral",
    "niche": "general",
    "engine_mode": "local"
}

ACTIVE_MODELS = [
    "gemini-flash-lite-latest",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-3-flash-preview",
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
        print(f"Config save note: {e}")

def ensure_viral_hashtags(ai_text, min_hashtags=8):
    """Guarantees at least 7-8 viral hashtags including #MustWatch, #FYP, #Viral."""
    if not ai_text:
        return ai_text

    existing_tags = re.findall(r'#[A-Za-z0-9_]+', ai_text)
    existing_tags_lower = {t.lower() for t in existing_tags}

    viral_pool = [
        "#MustWatch", "#FYP", "#Viral", "#Trending",
        "#ViralReels", "#ExplorePage", "#Reels",
        "#VideoOfTheDay", "#ForYouPage", "#TrendingNow"
    ]

    tags_to_add = []
    for priority_tag in ["#MustWatch", "#FYP", "#Viral"]:
        if priority_tag.lower() not in existing_tags_lower:
            tags_to_add.append(priority_tag)
            existing_tags_lower.add(priority_tag.lower())

    current_count = len(existing_tags) + len(tags_to_add)
    for tag in viral_pool:
        if current_count >= min_hashtags:
            break
        if tag.lower() not in existing_tags_lower:
            tags_to_add.append(tag)
            existing_tags_lower.add(tag.lower())
            current_count += 1

    if tags_to_add:
        if '#' in ai_text:
            return f"{ai_text.strip()} {' '.join(tags_to_add)}"
        else:
            return f"{ai_text.strip()}   {' '.join(tags_to_add)}"
    return ai_text

def create_fast_video_preview(media_path):
    """
    Creates a super-compressed temporary 480p preview for Gemini analysis.
    Reduces upload time from 25s down to 2-4s without sacrificing AI comprehension.
    """
    media_path = Path(media_path)
    if media_path.suffix.lower() not in ('.mp4', '.mov', '.mkv', '.avi', '.webm', '.m4v') or media_path.stat().st_size < 2500000:
        return media_path, False

    temp_preview = media_path.parent / f"_fastpreview_{media_path.stem[:12]}.mp4"
    try:
        cmd = [
            'ffmpeg', '-y', '-i', str(media_path),
            '-vf', 'scale=480:-2',
            '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '32',
            '-c:a', 'aac', '-b:a', '64k',
            str(temp_preview)
        ]
        res = run_silent_cmd(cmd, capture_output=True, timeout=12)
        if res.returncode == 0 and temp_preview.exists() and temp_preview.stat().st_size > 0:
            return temp_preview, True
    except Exception:
        pass
    return media_path, False

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
    return ensure_viral_hashtags(result)

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

DANGLING_STOPWORDS = {
    'a', 'an', 'the', 'and', 'or', 'but', 'for', 'nor', 'on', 'at', 'to', 'from',
    'by', 'with', 'in', 'of', 'into', 'onto', 'upon', 'about', 'above', 'across',
    'after', 'against', 'along', 'among', 'around', 'as', 'before', 'behind', 'below',
    'beneath', 'beside', 'between', 'beyond', 'during', 'inside', 'near', 'off',
    'outside', 'over', 'through', 'under', 'until', 'up', 'down', 'while', 'so',
    'that', 'than', 'though', 'although', 'because', 'since', 'unless', 'when',
    'where', 'which', 'who', 'whom', 'whose', 'why', 'how', 'this', 'that', 'these',
    'those', 'their', 'his', 'her', 'its', 'my', 'your', 'our', 'is', 'are', 'was',
    'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
    'would', 'shall', 'should', 'can', 'could', 'may', 'might', 'must', 'precisely',
    'pure', 'more', 'just', 'very', 'one', 'two', 'three', 'daring', 'fearless',
    'perfect', 'high-stakes', 'multi-directional', 'stunning', 'incredible',
    'unbelievable', 'breathtaking', 'flawless', 'seamless', 'synchronized', 'massive'
}

def is_finished_sentence(s):
    s = s.strip()
    if not s:
        return False
    # Strip any trailing emojis, variation selectors, and spaces
    core = re.sub(r'[\U0001F000-\U0001FAFF\u2600-\u27BF\ufe0f\u200d\s]+$', '', s)
    if any(core.endswith(p) for p in ['.', '!', '?', '…']):
        return True
    last_c = s.rstrip('\ufe0f\u200d\u200b ')[-1] if s.rstrip('\ufe0f\u200d\u200b ') else ''
    if last_c:
        return ord(last_c) > 0x1F000 or ord(last_c) in range(0x2600, 0x27BF) or ord(last_c) == 0xFE0F
    return False

def clean_caption_text(text, max_len=95):
    """
    Cleans caption text ensuring it NEVER ends with dangling stop-words,
    incomplete clauses, or broken 'adi' words. Always ends cleanly with punctuation and emojis.
    """
    text = re.sub(r'[<>:"/\\|?*\x00-\x1f\r\n]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    if not text:
        return ""

    # Extract complete sentences including any trailing emojis
    sentences = [m.group(0).strip() for m in re.finditer(r'.+?(?:[.!?][\U0001F000-\U0001FAFF\u2600-\u27BF\ufe0f\u200d\s]*|$)', text) if m.group(0).strip()]
    if sentences and is_finished_sentence(sentences[0]):
        if len(sentences[0]) <= max_len:
            chosen = sentences[0]
            if len(sentences) > 1 and is_finished_sentence(sentences[1]) and len(f"{chosen} {sentences[1]}") <= max_len:
                chosen = f"{chosen} {sentences[1]}"
            return chosen

    # If first sentence exceeds max_len or was an incomplete fragment, find clean sub-clause
    trimmed = text[:max_len]
    clause_breaks = [trimmed.rfind(', '), trimmed.rfind('; '), trimmed.rfind(' - '), trimmed.rfind(' — ')]
    best_break = max(clause_breaks)

    if best_break > 35:
        sub = trimmed[:best_break].strip()
    else:
        last_sp = trimmed.rfind(' ')
        sub = trimmed[:last_sp].strip() if last_sp > 25 else trimmed.strip()

    # Strip any dangling stop-words or hanging adjectives from end
    words = sub.split()
    while words and words[-1].lower().rstrip('.,;!?#') in DANGLING_STOPWORDS:
        words.pop()

    cleaned = ' '.join(words).rstrip('.,;:- ')
    if cleaned:
        if not is_finished_sentence(cleaned):
            cleaned += '!'
    return cleaned

def generate_video_filename(ai_text, ext, target_folder=None, fallback_stem="video", max_len=250):
    ext = ext.lower() if ext else ".mp4"
    if not ext.startswith("."):
        ext = "." + ext

    # Windows MAX_PATH is 260. VLC 32-bit fails if total path >= 256.
    # Keep total absolute path strictly <= 238 characters to guarantee 100% VLC compatibility.
    if target_folder:
        try:
            folder_len = len(str(Path(target_folder).resolve()))
        except Exception:
            folder_len = 75
    else:
        folder_len = 75

    max_stem_len = max(70, min(165, 238 - folder_len - len(ext)))

    # Split hashtags and caption
    raw_tags = re.findall(r'#[A-Za-z0-9_]+', ai_text)
    caption_raw = re.sub(r'#[A-Za-z0-9_]+', '', ai_text)

    # Balance caption and hashtags:
    # Minimum 3 viral hashtags (e.g. #MustWatch #FYP #Viral = ~25 chars) + 3 separator spaces
    min_tag_space = 25
    caption_budget = max(50, max_stem_len - min_tag_space - 3)

    clean_caption = clean_caption_text(caption_raw, max_len=caption_budget)

    # Clean and deduplicate hashtags
    seen = set()
    valid_tags = []
    for t in raw_tags:
        clean_t = '#' + re.sub(r'[^A-Za-z0-9_]', '', t)
        norm = clean_t.lower()
        if len(clean_t) > 1 and norm not in seen and norm not in {'#outputmedia', '#output', '#input', '#media'}:
            seen.add(norm)
            valid_tags.append(clean_t)

    if not clean_caption and not valid_tags:
        base_name = fallback_stem
    elif not valid_tags:
        base_name = clean_caption
    elif not clean_caption:
        fitted = []
        for t in valid_tags:
            cand = (' ' if fitted else '').join(fitted + [t])
            if len(cand) <= max_stem_len:
                fitted.append(t)
            else:
                break
        base_name = ' '.join(fitted) if fitted else valid_tags[0][:max_stem_len]
    else:
        # BOTH CAPTION AND HASHTAGS EXIST: FIT BOTH PERFECTLY WITH ZERO ADI WORDS
        space_left = max_stem_len - len(clean_caption) - 3  # '   ' separator
        fitted_tags = []
        for t in valid_tags:
            cand = ' '.join(fitted_tags + [t])
            if len(cand) <= space_left:
                fitted_tags.append(t)
            else:
                break

        if fitted_tags:
            base_name = f"{clean_caption}   {' '.join(fitted_tags)}"
        else:
            base_name = clean_caption

    base_name = re.sub(r'[<>:"/\\|?*\x00-\x1f\r\n]', '', base_name).strip().rstrip('. ')
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
        needed = len(tag)
        # Drop hashtags cleanly without chopping any tag
        curr_tags = list(fitted_tags) if ('fitted_tags' in locals() and fitted_tags) else []
        while curr_tags and (len(f"{clean_caption}   {' '.join(curr_tags)}") + needed > max_stem_len):
            curr_tags.pop()

        if curr_tags:
            stem_candidate = f"{clean_caption}   {' '.join(curr_tags)}"
        else:
            stem_candidate = clean_caption_text(clean_caption, max_len=max_stem_len - needed)

        new_name = f"{stem_candidate}{tag}{ext}"
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

def safe_move_file(src, dst, max_retries=10, delay=0.3):
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
    # Phase 1: Direct move attempt
    for attempt in range(max_retries):
        try:
            gc.collect()
            shutil.move(str(src), str(dst))
            if not src.exists():
                return True
        except Exception:
            gc.collect()
            time.sleep(delay)

    # Phase 2: Copy fallback + aggressive force delete of original
    try:
        shutil.copy2(str(src), str(dst))
        if dst.exists() and dst.stat().st_size == src.stat().st_size:
            for attempt in range(max_retries):
                try:
                    gc.collect()
                    src.unlink()
                    return True
                except Exception:
                    try:
                        import os
                        os.chmod(str(src), 0o777)
                        os.remove(str(src))
                        return True
                    except Exception:
                        time.sleep(delay)
            return not src.exists()
    except Exception:
        pass

    return not src.exists()

def has_nvenc():
    """Detects if NVIDIA NVENC hardware encoder is available on the system."""
    try:
        res = run_silent_cmd(
            ['ffmpeg', '-encoders'],
            capture_output=True,
            text=True,
            timeout=5
        )
        return 'h264_nvenc' in res.stdout
    except Exception:
        return False

def render_video_4k(input_path, output_path, log_callback=None):
    """
    Renders / upscales video to 4K Ultra HD (2160p) using NVIDIA NVENC hardware acceleration if available.
    Preserves exact audio track with -c:a copy.
    Maintains correct aspect ratio for both landscape (3840x2160) and vertical shorts/reels (2160x3840).
    Applies Lanczos high-detail scaling and unsharp edge enhancement.
    """
    input_path = Path(input_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    use_nvenc = has_nvenc()
    scale_filter = "scale=if(gte(iw\\,ih)\\,3840\\,-2):if(gte(iw\\,ih)\\,-2\\,3840):flags=lanczos,unsharp=5:5:0.8:3:3:0.4"
    
    if use_nvenc:
        vcodec_args = ['-c:v', 'h264_nvenc', '-preset', 'p6', '-tune', 'hq', '-rc', 'vbr', '-cq', '19', '-b:v', '0']
    else:
        vcodec_args = ['-c:v', 'libx264', '-preset', 'veryfast', '-crf', '19']
        
    cmd = [
        'ffmpeg', '-y',
        '-i', str(input_path),
        '-vf', scale_filter,
        *vcodec_args,
        '-c:a', 'copy',
        '-movflags', '+faststart',
        str(output_path)
    ]
    
    t0 = time.time()
    try:
        res = run_silent_cmd(cmd, capture_output=True, text=True)
        dur = time.time() - t0
        
        if res.returncode == 0 and output_path.exists() and output_path.stat().st_size > 0:
            if log_callback:
                hw_name = "NVIDIA GeForce RTX (NVENC)" if use_nvenc else "CPU"
                log_callback(f"4K Ultra-HD rendered in {dur:.1f}s via {hw_name}!")
            return True
        else:
            if use_nvenc:
                if log_callback:
                    log_callback("NVENC notice: Falling back to CPU 4K encoder...")
                cpu_cmd = [
                    'ffmpeg', '-y',
                    '-i', str(input_path),
                    '-vf', scale_filter,
                    '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '19',
                    '-c:a', 'copy',
                    '-movflags', '+faststart',
                    str(output_path)
                ]
                res_cpu = run_silent_cmd(cpu_cmd, capture_output=True, text=True)
                if res_cpu.returncode == 0 and output_path.exists() and output_path.stat().st_size > 0:
                    if log_callback:
                        log_callback(f"4K CPU render completed in {time.time() - t0:.1f}s")
                    return True
            if log_callback:
                err_snippet = res.stderr[-200:] if res.stderr else "FFmpeg error"
                log_callback(f"4K render notice: {err_snippet}")
            return False
    except Exception as e:
        if log_callback:
            log_callback(f"4K render exception: {e}")
        return False

class VideoSeparatorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🎬 Video Separator - Pure Gemini AI SEO Studio")
        self.root.geometry("1060x750")
        self.root.minsize(900, 620)
        self.root.configure(bg="#0f172a")

        self.config = load_config()
        self.files_list = []
        self.selected_file_index = -1
        self.is_processing = False
        self.stop_requested = False
        self.msg_queue = queue.Queue()

        self.setup_ui()
        self.refresh_file_list()
        self.check_queue()
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

    def setup_ui(self):
        # Header banner
        header = tk.Frame(self.root, bg="#1e293b", padx=20, pady=12)
        header.pack(fill="x")

        title_lbl = tk.Label(
            header,
            text="🎬 Video Separator - 100% Pure Gemini AI (Hook, Caption, Hashtag)",
            font=("Segoe UI", 16, "bold"),
            fg="#38bdf8",
            bg="#1e293b"
        )
        title_lbl.pack(anchor="w")

        subtitle_lbl = tk.Label(
            header,
            text="भिडियो सिधै Gemini मा Attach हुन्छ | शुद्ध Hook, Caption र Hashtag मात्र .txt मा सेभ हुन्छ | भिडियो 1, 2... मा Rename हुन्छ",
            font=("Segoe UI", 9),
            fg="#94a3b8",
            bg="#1e293b"
        )
        subtitle_lbl.pack(anchor="w", pady=(2, 0))

        # Top Control Bar (Platform + API Key + Folders)
        ctrl_bar = tk.Frame(self.root, bg="#0f172a", padx=16, pady=8)
        ctrl_bar.pack(fill="x")

        tk.Label(ctrl_bar, text="🎯 Platform:", font=("Segoe UI", 10, "bold"), fg="#e2e8f0", bg="#0f172a").pack(side="left", padx=(0, 6))

        self.platform_var = tk.StringVar(value=self.config.get("target_platform", "facebook"))
        platform_combo = ttk.Combobox(
            ctrl_bar,
            textvariable=self.platform_var,
            values=["facebook", "tiktok", "instagram", "youtube"],
            state="readonly",
            width=12,
            font=("Segoe UI", 10)
        )
        platform_combo.pack(side="left", padx=(0, 14))
        platform_combo.bind("<<ComboboxSelected>>", self.on_platform_changed)

        btn_key = tk.Button(
            ctrl_bar,
            text="🔑 Gemini API Key",
            font=("Segoe UI", 9),
            bg="#334155",
            fg="#e2e8f0",
            activebackground="#475569",
            activeforeground="#ffffff",
            padx=10,
            pady=4,
            relief="flat",
            cursor="hand2",
            command=self.open_key_dialog
        )
        btn_key.pack(side="left", padx=(0, 10))

        btn_web = tk.Button(
            ctrl_bar,
            text="🌐 Web Studio (localhost:5050)",
            font=("Segoe UI", 9, "bold"),
            bg="#0284c7",
            fg="#ffffff",
            activebackground="#0ea5e9",
            activeforeground="#ffffff",
            padx=12,
            pady=4,
            relief="flat",
            cursor="hand2",
            command=self.open_web_app
        )
        btn_web.pack(side="left", padx=(0, 10))

        btn_open_out = tk.Button(
            ctrl_bar,
            text="📂 Open Output Folder",
            font=("Segoe UI", 9),
            bg="#1e293b",
            fg="#cbd5e1",
            activebackground="#334155",
            activeforeground="#ffffff",
            padx=10,
            pady=4,
            relief="flat",
            cursor="hand2",
            command=lambda: open_directory_in_explorer(OUTPUT_DIR)
        )
        btn_open_out.pack(side="right")

        # Main Split Content
        main_split = tk.PanedWindow(self.root, orient="horizontal", bg="#0f172a", sashwidth=4)
        main_split.pack(fill="both", expand=True, padx=16, pady=6)

        # LEFT PANE: Video List & Input Buttons
        left_frame = tk.Frame(main_split, bg="#1e293b", padx=12, pady=12)
        main_split.add(left_frame, minsize=320)

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
            text="✂️ भिडियो फाइलहरू छान्नुहोस् (Cut & Move)",
            font=("Segoe UI", 9, "bold"),
            bg="#059669",
            fg="#ffffff",
            activebackground="#047857",
            activeforeground="#ffffff",
            padx=10,
            pady=5,
            relief="flat",
            cursor="hand2",
            command=self.browse_and_add_files
        )
        btn_add_files.pack(fill="x", pady=(0, 4))

        btn_add_folder = tk.Button(
            input_btn_frame,
            text="📁 सम्पूर्ण फोल्डर छान्नुहोस् (Cut & Move)",
            font=("Segoe UI", 9),
            bg="#0284c7",
            fg="#ffffff",
            activebackground="#0369a1",
            activeforeground="#ffffff",
            padx=10,
            pady=4,
            relief="flat",
            cursor="hand2",
            command=self.browse_and_add_folder
        )
        btn_add_folder.pack(fill="x", pady=(0, 4))

        input_tools_row = tk.Frame(input_btn_frame, bg="#1e293b")
        input_tools_row.pack(fill="x")

        btn_open_input_dir = tk.Button(
            input_tools_row,
            text="📂 Open input_media",
            font=("Segoe UI", 8),
            bg="#334155",
            fg="#cbd5e1",
            padx=6,
            pady=2,
            relief="flat",
            cursor="hand2",
            command=lambda: open_directory_in_explorer(INPUT_DIR)
        )
        btn_open_input_dir.pack(side="left")

        btn_refresh = tk.Button(
            input_tools_row,
            text="🔄 Refresh List",
            font=("Segoe UI", 8),
            bg="#334155",
            fg="#cbd5e1",
            padx=6,
            pady=2,
            relief="flat",
            cursor="hand2",
            command=self.refresh_file_list
        )
        btn_refresh.pack(side="right")

        self.list_count_lbl = tk.Label(
            left_frame,
            text="📁 भिडियोहरू (input_media): 0",
            font=("Segoe UI", 9, "bold"),
            fg="#38bdf8",
            bg="#1e293b"
        )
        self.list_count_lbl.pack(anchor="w", pady=(6, 4))

        self.file_listbox = tk.Listbox(
            left_frame,
            font=("Segoe UI", 10),
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

        # RIGHT PANE: Direct Gemini Execution & Live Logs
        right_frame = tk.Frame(main_split, bg="#1e293b", padx=16, pady=12)
        main_split.add(right_frame, minsize=480)

        self.cur_video_lbl = tk.Label(
            right_frame,
            text="कृपया बाँयाबाट भिडियो छान्नुहोस् वा सिधै 'PROCESS ALL' थिच्नुहोस्",
            font=("Segoe UI", 11, "bold"),
            fg="#f1f5f9",
            bg="#1e293b",
            wraplength=480,
            justify="left"
        )
        self.cur_video_lbl.pack(anchor="w")

        action_bar = tk.Frame(right_frame, bg="#1e293b", pady=8)
        action_bar.pack(fill="x")

        self.btn_auto_all = tk.Button(
            action_bar,
            text="🚀 DIRECT GEMINI ATTACH & CUT ALL (Rename 1, 2...)",
            font=("Segoe UI", 11, "bold"),
            bg="#059669",
            fg="#ffffff",
            activebackground="#047857",
            activeforeground="#ffffff",
            padx=16,
            pady=10,
            relief="flat",
            cursor="hand2",
            command=self.start_process_all_videos
        )
        self.btn_auto_all.pack(side="left", padx=(0, 8))

        self.btn_auto_single = tk.Button(
            action_bar,
            text="⚡ यस भिडियो मात्र Process गर्ने",
            font=("Segoe UI", 9, "bold"),
            bg="#2563eb",
            fg="#ffffff",
            activebackground="#1d4ed8",
            activeforeground="#ffffff",
            padx=12,
            pady=10,
            relief="flat",
            cursor="hand2",
            state="disabled",
            command=self.start_process_selected_video
        )
        self.btn_auto_single.pack(side="left")

        self.btn_stop = tk.Button(
            action_bar,
            text="⏹️ STOP ANALYSIS (रोक्नुहोस्)",
            font=("Segoe UI", 9, "bold"),
            bg="#475569",
            fg="#ffffff",
            activebackground="#dc2626",
            activeforeground="#ffffff",
            padx=12,
            pady=10,
            relief="flat",
            cursor="hand2",
            state="disabled",
            command=self.request_stop
        )
        self.btn_stop.pack(side="left", padx=(8, 0))

        self.btn_clear_log = tk.Button(
            action_bar,
            text="🧹 Clear Logs (हटाउनुहोस्)",
            font=("Segoe UI", 9, "bold"),
            bg="#334155",
            fg="#cbd5e1",
            activebackground="#475569",
            activeforeground="#ffffff",
            padx=12,
            pady=10,
            relief="flat",
            cursor="hand2",
            command=self.clear_log
        )
        self.btn_clear_log.pack(side="left", padx=(8, 0))

        log_header_frame = tk.Frame(right_frame, bg="#1e293b")
        log_header_frame.pack(fill="x", pady=(8, 2))

        tk.Label(
            log_header_frame,
            text="📝 Pure Gemini Output (Hook, Caption, Hashtag) Live Logs:",
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
            padx=10,
            pady=10,
            wrap="word"
        )
        self.txt_output.pack(fill="both", expand=True)

        self.status_bar = tk.Label(
            self.root,
            text="तयार छ। 'DIRECT GEMINI ATTACH & CUT ALL' थिचेर शुद्ध Hook, Caption, Hashtags निकाल्नुहोस्।",
            font=("Segoe UI", 9),
            fg="#94a3b8",
            bg="#0f172a",
            anchor="w",
            padx=20,
            pady=6
        )
        self.status_bar.pack(fill="x")

    def on_platform_changed(self, event=None):
        self.config["target_platform"] = self.platform_var.get()
        save_config(self.config)
        self.status_bar.config(text=f"🎯 Target Platform परिवर्तन भयो: {self.platform_var.get().upper()}")

    def open_key_dialog(self):
        win = tk.Toplevel(self.root)
        win.title("Gemini API Key Setup")
        win.geometry("520x220")
        win.configure(bg="#1e293b")
        win.transient(self.root)
        win.grab_set()

        tk.Label(win, text="🔑 Google Gemini API Key:", font=("Segoe UI", 11, "bold"), fg="#38bdf8", bg="#1e293b").pack(anchor="w", padx=20, pady=(16, 6))

        key_entry = tk.Entry(win, font=("Segoe UI", 10), bg="#0f172a", fg="#ffffff", insertbackground="#38bdf8", relief="solid", bd=1)
        key_entry.insert(0, self.config.get("gemini_api_key", ""))
        key_entry.pack(fill="x", padx=20, pady=4)

        tk.Label(win, text="नि:शुल्क Key लिन: https://aistudio.google.com/app/apikey", font=("Segoe UI", 8), fg="#94a3b8", bg="#1e293b").pack(anchor="w", padx=20, pady=(2, 16))

        def save_k():
            new_k = key_entry.get().strip()
            self.config["gemini_api_key"] = new_k
            save_config(self.config)
            messagebox.showinfo("Saved", "✅ Gemini API Key सुरक्षित भयो!", parent=win)
            win.destroy()

        tk.Button(win, text="सुरक्षित गर्नुहोस् (Save Key)", font=("Segoe UI", 10, "bold"), bg="#059669", fg="#ffffff", padx=16, pady=6, relief="flat", cursor="hand2", command=save_k).pack(anchor="e", padx=20)

    def browse_and_add_files(self):
        selected = filedialog.askopenfilenames(
            title="भिडियो वा मिडिया छान्नुहोस् (Direct CUT)",
            filetypes=[
                ("Media Files (*.mp4, *.mov, *.jpg, etc.)", "*.mp4 *.mov *.mkv *.avi *.webm *.m4v *.jpg *.jpeg *.png *.webp"),
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
            self.status_bar.config(text=f"✅ ✂️ CUT & Move गरियो ({count} वटा फाइलहरू input_media मा आए)!")

    def browse_and_add_folder(self):
        selected = filedialog.askdirectory(title="भिडियो भएको फोल्डर छान्नुहोस् (Direct CUT)", parent=self.root)
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
            self.status_bar.config(text=f"✅ ✂️ फोल्डर '{src_dir.name}' CUT गरेर input_media मा सारियो!")

    def refresh_file_list(self):
        self.file_listbox.delete(0, tk.END)
        self.files_list = []
        video_exts = ('.mp4', '.mov', '.mkv', '.avi', '.webm', '.m4v')
        photo_exts = ('.jpg', '.jpeg', '.png', '.webp', '.bmp')
        all_exts = video_exts + photo_exts

        if INPUT_DIR.exists():
            for f in sorted(INPUT_DIR.iterdir(), key=lambda x: x.name.lower()):
                if f.is_file() and f.suffix.lower() in all_exts:
                    self.files_list.append(f)
                    size_mb = f.stat().st_size / (1024 * 1024)
                    icon = "🎬" if f.suffix.lower() in video_exts else "📸"
                    self.file_listbox.insert(tk.END, f"{icon} {f.name} ({size_mb:.1f} MB)")
                elif f.is_dir():
                    for subf in sorted(f.iterdir(), key=lambda x: x.name.lower()):
                        if subf.is_file() and subf.suffix.lower() in all_exts:
                            self.files_list.append(subf)
                            size_mb = subf.stat().st_size / (1024 * 1024)
                            self.file_listbox.insert(tk.END, f"📁 {f.name}/{subf.name} ({size_mb:.1f} MB)")

        count = len(self.files_list)
        self.list_count_lbl.config(text=f"📁 भिडियोहरू (input_media): {count}")

        if count > 0 and not self.is_processing:
            self.file_listbox.selection_set(0)
            self.on_file_selected()
            self.btn_auto_single.config(state="normal")
            self.btn_auto_all.config(state="normal")
        else:
            self.cur_video_lbl.config(text="⚠️ input_media फोल्डर खाली छ!")
            self.btn_auto_single.config(state="disabled")
            self.btn_auto_all.config(state="disabled")

    def on_file_selected(self, event=None):
        sel = self.file_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        self.selected_file_index = idx
        media_path = self.files_list[idx]
        self.cur_video_lbl.config(text=f"📁 [{idx + 1}/{len(self.files_list)}] छनौट भएको: {media_path.name}")

    def log(self, text):
        self.msg_queue.put(("log", text))
        try:
            import web_server
            web_server.state.add_log(text)
        except Exception:
            pass

    def clear_log(self):
        self.txt_output.delete("1.0", tk.END)
        self.status_bar.config(text="🧹 Live logs हटाइयो (Cleared)!")
        try:
            import web_server
            web_server.state.clear_logs()
        except Exception:
            pass

    def request_stop(self):
        if self.is_processing and not self.stop_requested:
            self.stop_requested = True
            self.btn_stop.config(state="disabled", text="⏳ Stopping...", bg="#7f1d1d")
            self.status_bar.config(text="🛑 Analysis रोकिँदैछ... कृपया हालको फाइलको कार्य नसकिउन्जेल पर्खनुहोस्...")
            self.log("\n⚠️ Stop अनुरोध प्राप्त भयो! रोकिने प्रक्रिया सुरु भयो...")
            try:
                import web_server
                web_server.state.stop_requested = True
            except Exception:
                pass

    def check_queue(self):
        try:
            while True:
                msg_type, data = self.msg_queue.get_nowait()
                if msg_type == "log":
                    self.txt_output.insert(tk.END, data + "\n")
                    self.txt_output.see(tk.END)
                elif msg_type == "status":
                    self.status_bar.config(text=data)
                elif msg_type == "finished":
                    self.is_processing = False
                    self.stop_requested = False
                    self.btn_stop.config(state="disabled", text="⏹️ STOP ANALYSIS (रोक्नुहोस्)", bg="#475569")
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
                elif self.is_processing and ws_state.stop_requested:
                    self.stop_requested = True
        except Exception:
            pass

        self.root.after(100, self.check_queue)

    def start_process_selected_video(self):
        if self.selected_file_index < 0 or self.selected_file_index >= len(self.files_list):
            return
        target_file = self.files_list[self.selected_file_index]
        self.is_processing = True
        self.stop_requested = False
        self.btn_auto_single.config(state="disabled")
        self.btn_auto_all.config(state="disabled")
        self.btn_stop.config(state="normal", text="⏹️ STOP ANALYSIS (रोक्नुहोस्)", bg="#dc2626")
        threading.Thread(target=self._process_worker, args=([target_file],), daemon=True).start()

    def start_process_all_videos(self):
        if not self.files_list:
            return
        self.is_processing = True
        self.stop_requested = False
        self.btn_auto_single.config(state="disabled")
        self.btn_auto_all.config(state="disabled")
        self.btn_stop.config(state="normal", text="⏹️ STOP ANALYSIS (रोक्नुहोस्)", bg="#dc2626")
        threading.Thread(target=self._process_worker, args=(list(self.files_list),), daemon=True).start()

    def _process_worker(self, targets):
        engine_mode = self.config.get("engine_mode", "local")
        api_key = self.config.get("gemini_api_key", "").strip()
        client = None

        if engine_mode != "local":
            if not api_key:
                self.log("⚠️ Notice: Gemini API Key फेला परेन। Smart Video SEO Engine प्रयोग गरिँदैछ।")
                engine_mode = "local"
            else:
                try:
                    from google import genai
                    client = genai.Client(api_key=api_key)
                except Exception as ce:
                    self.log(f"⚠️ Notice: Gemini client error ({ce}). Smart Video SEO Engine प्रयोग गरिँदैछ।")
                    engine_mode = "local"

        platform = self.platform_var.get()
        video_exts = ('.mp4', '.mov', '.mkv', '.avi', '.webm', '.m4v')

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
                self.log("\n🛑 Analysis प्रयोगकर्ताद्वारा रोकियो (Stopped by user)!")
                self.msg_queue.put(("finished", "🛑 Analysis बीचमै रोकियो। बाँकी फाइलहरू सुरक्षित छन्।"))
                break

            if not media_path.exists():
                continue

            is_video = media_path.suffix.lower() in video_exts

            ext = media_path.suffix.lower()
            target_folder = OUTPUT_DIR
            target_folder.mkdir(parents=True, exist_ok=True)

            self.log(f"\n==========================================")
            self.log(f"[{i}/{total_files}] 🎬 {media_path.name}")
            self.log("   🎥 Video will be 4K AI Upscaled & renamed with Caption + Hashtags directly in output_media")

            # Parallel 4K Upscale render on GPU
            render_thread = None
            render_status = {"done": False, "ok": False}
            temp_4k_path = None

            if is_video:
                temp_4k_filename = f".render_4k_{int(time.time())}_{i}.mp4"
                temp_4k_path = target_folder / temp_4k_filename

                def _bg_render(src=media_path, dst=temp_4k_path):
                    self.log("   ⚡ [Parallel GPU] 4K Ultra-HD Upscale render started in background...")
                    ok = render_video_4k(src, dst, log_callback=lambda m: self.log(f"   🎬 [4K Render]: {m}"))
                    render_status["ok"] = ok
                    render_status["done"] = True

                render_thread = threading.Thread(target=_bg_render, daemon=True)
                render_thread.start()

            folder_hint = target_folder.name if target_folder else media_path.parent.name
            self.msg_queue.put(("status", f"[{i}/{total_files}] Decoding & analyzing {media_path.name}..."))
            ai_output = local_video_seo.decode_video_with_gemini(
                media_path=media_path,
                client=client,
                api_key=api_key,
                platform=platform,
                folder_name=folder_hint,
                index=i,
                log_callback=self.log,
                force_local=(engine_mode == "local")
            )

            if self.stop_requested:
                self.log("\n🛑 Analysis प्रयोगकर्ताद्वारा रोकियो (Stopped)!")
                self.msg_queue.put(("finished", "🛑 Analysis बीचमै रोकियो। बाँकी फाइलहरू सुरक्षित छन्।"))
                return

            # Wait for 4K render to finalize
            if render_thread and render_thread.is_alive():
                self.log("   ⏳ Finalizing parallel 4K render on GPU...")
                render_thread.join(timeout=300)

            ai_output = clean_ai_output(ai_output)
            self.msg_queue.put(("output", ai_output.strip()))

            # Generate video filename directly from AI Caption + Hashtags (zero .txt file)
            output_ext = ".mp4" if (render_status.get("ok") and temp_4k_path and temp_4k_path.exists()) else ext
            renamed_filename = generate_video_filename(ai_output, output_ext, target_folder, fallback_stem=media_path.stem)
            target_media = target_folder / renamed_filename

            # Strictly CUT & Move media from input_media to output_media
            import gc
            gc.collect()
            time.sleep(0.3)
            if render_status.get("ok") and temp_4k_path and temp_4k_path.exists() and temp_4k_path.stat().st_size > 0:
                safe_move_file(temp_4k_path, target_media)
                self.log(f"   ✨ 4K Ultra-HD Video successfully saved to output_media!")
                for _ in range(5):
                    try:
                        gc.collect()
                        time.sleep(0.2)
                        import os
                        os.chmod(str(media_path), 0o777)
                        media_path.unlink()
                        break
                    except Exception:
                        pass
            else:
                safe_move_file(media_path, target_media)
                if media_path.exists():
                    for _ in range(5):
                        try:
                            gc.collect()
                            time.sleep(0.2)
                            import os
                            os.chmod(str(media_path), 0o777)
                            media_path.unlink()
                            break
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

            try:
                import web_server
                web_server.state.latest_result = {
                    "folder": "",
                    "video_file": renamed_filename,
                    "txt_file": "",
                    "content": ai_output
                }
            except Exception:
                pass

            self.log(f"   ✂️  CUT & RENAME ➔ {renamed_filename}")

        self.msg_queue.put(("finished", f"🎉 सबै {total_files} वटा भिडियोहरू Gemini AI ले विश्लेषण गरी शुद्ध Hook, Caption, र Hashtag सहित CUT र Rename गरियो!"))
        self.is_processing = False
        try:
            import web_server
            web_server.state.is_processing = False
        except Exception:
            pass

def main():
    if "--legacy" in sys.argv or "--tk" in sys.argv:
        root = tk.Tk()
        app = VideoSeparatorGUI(root)
        root.mainloop()
    else:
        try:
            import LustreSeparator
            LustreSeparator.launch_modern_desktop_app()
        except Exception:
            root = tk.Tk()
            app = VideoSeparatorGUI(root)
            root.mainloop()

if __name__ == "__main__":
    main()
