#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Lustre Separator - Web Server & REST API
Pure Gemini Video Analysis & Media Renaming Engine (Online Mode)
Provides a modern Web Application running in your browser:
- Direct Gemini AI Video Analysis online
- Pure English Hook, Caption, and Hashtags
- Unchanged folder names, videos renamed to 1.mp4, 2.mp4...
- Real-time Web UI with Start, Stop, Logs, and File Management
"""

import os
import sys
import shutil
import time
import json
import threading
import subprocess
import mimetypes
import webbrowser
import re
from pathlib import Path
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import auto_updater
import local_video_seo

# Safe streams for pythonw & UTF-8 stdout on Windows
if sys.stdout is None:
    try:
        sys.stdout = open(os.devnull, 'w', encoding='utf-8')
    except Exception:
        pass
if sys.stderr is None:
    try:
        sys.stderr = open(os.devnull, 'w', encoding='utf-8')
    except Exception:
        pass

if sys.platform.startswith('win'):
    try:
        if sys.stdout is not None and hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        if sys.stderr is not None and hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

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

# Base Directories
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
    "niche": "general",
    "upscale_4k": False,
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

def parse_api_keys(raw_keys):
    """Splits comma, semicolon, space, or newline delimited Gemini API keys."""
    if not raw_keys:
        return []
    if isinstance(raw_keys, list):
        return [k.strip() for k in raw_keys if k and k.strip()]
    return [k.strip() for k in re.split(r'[,;\n\r\s]+', str(raw_keys)) if k.strip()]

class GeminiKeyRotator:
    def __init__(self, raw_keys):
        self.keys = parse_api_keys(raw_keys)
        self.current_idx = 0
        self._lock = threading.Lock()

    def get_client(self):
        with self._lock:
            if not self.keys:
                return None, 0, 0
            idx = self.current_idx % len(self.keys)
            key = self.keys[idx]
            from google import genai
            return genai.Client(api_key=key), idx, len(self.keys)

    def rotate(self):
        with self._lock:
            if len(self.keys) > 1:
                self.current_idx = (self.current_idx + 1) % len(self.keys)
                return True
            return False

    @property
    def total_keys(self):
        return len(self.keys)

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
        print(f"Error saving config: {e}")

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

def generate_video_filename(ai_text, ext, target_folder=None, fallback_stem="video", max_len=250):
    ext = ext.lower() if ext else ".mp4"
    if not ext.startswith("."):
        ext = "." + ext

    # 255 characters is Windows NTFS max filename limit.
    # Leaving room for extension (.mp4 is 4 chars) and potential collision tag ' (1)' (4 chars):
    max_stem_len = min(max_len, 255 - len(ext))

    # Split hashtags and caption
    hashtags = re.findall(r'#[A-Za-z0-9_]+', ai_text)
    caption_part = re.sub(r'#[A-Za-z0-9_]+', '', ai_text)
    caption_part = re.sub(r'[\r\n\t]+', ' ', caption_part)
    caption_part = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '', caption_part)
    caption_part = re.sub(r'\s+', ' ', caption_part).strip().rstrip('. ')

    if not caption_part and not hashtags:
        base_name = fallback_stem
    elif not hashtags:
        if len(caption_part) <= max_stem_len:
            base_name = caption_part
        else:
            trimmed = caption_part[:max_stem_len]
            last_sp = trimmed.rfind(' ')
            base_name = trimmed[:last_sp].rstrip('. ') if last_sp > 50 else trimmed.rstrip('. ')
    elif not caption_part:
        fitted = []
        for tag in hashtags:
            test = ' '.join(fitted + [tag])
            if len(test) <= max_stem_len:
                fitted.append(tag)
            else:
                break
        base_name = ' '.join(fitted) if fitted else hashtags[0][:max_stem_len]
    else:
        # Both caption and hashtags exist:
        if len(caption_part) <= max_stem_len:
            # Full caption fits! Now fit as many complete hashtags as possible
            space_left = max_stem_len - len(caption_part) - 3  # '   ' separator
            fitted_tags = []
            for tag in hashtags:
                test_str = ' '.join(fitted_tags + [tag])
                if len(test_str) <= space_left:
                    fitted_tags.append(tag)
                else:
                    break
            if fitted_tags:
                base_name = f"{caption_part}   {' '.join(fitted_tags)}"
            else:
                base_name = caption_part
        else:
            # Caption itself is longer than 250 characters (very rare)
            trimmed = caption_part[:max_stem_len]
            last_p = max(trimmed.rfind('. '), trimmed.rfind('! '), trimmed.rfind('? '))
            if last_p > int(max_stem_len * 0.6):
                complete_sentence = trimmed[:last_p + 1].strip()
                space_left = max_stem_len - len(complete_sentence) - 3
                fitted_tags = []
                for tag in hashtags:
                    test_str = ' '.join(fitted_tags + [tag])
                    if len(test_str) <= space_left:
                        fitted_tags.append(tag)
                    else:
                        break
                if fitted_tags:
                    base_name = f"{complete_sentence}   {' '.join(fitted_tags)}"
                else:
                    base_name = complete_sentence
            else:
                last_sp = trimmed.rfind(' ')
                base_name = trimmed[:last_sp].strip().rstrip('. ') if last_sp > 50 else trimmed.rstrip('. ')

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
        trimmed_base = base_name[:(max_stem_len - len(tag))].rstrip('. ')
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
            # 1. Direct explorer.exe with closed FDs (returns immediately, no DDE hang)
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
            # 2. cmd.exe /c start fallback
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
            # 3. os.startfile fallback
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
    
    # 4K scale expression:
    # If landscape (iw >= ih): width=3840, height auto-even (-2)
    # If portrait (iw < ih): height=3840, width auto-even (-2)
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
    
    startupinfo = None
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

def native_pick_and_cut_files():
    """Opens native Windows file dialog via isolated PowerShell and directly CUTS selected files into input_media."""
    ps_cmd = (
        "Add-Type -AssemblyName System.Windows.Forms; "
        "$d = New-Object System.Windows.Forms.OpenFileDialog; "
        "$d.Multiselect = $true; "
        "$d.Filter = 'Media Files (*.mp4;*.mov;*.mkv;*.avi;*.webm;*.m4v;*.jpg;*.png;*.webp)|*.mp4;*.mov;*.mkv;*.avi;*.webm;*.m4v;*.jpg;*.png;*.webp|All Files (*.*)|*.*'; "
        "$d.Title = 'Select Videos (Direct CUT into input_media)'; "
        "if ($d.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) { "
        "  $d.FileNames | ForEach-Object { Write-Output $_ } "
        "}"
    )
    try:
        res = run_silent_cmd(
            ['powershell', '-Sta', '-NoProfile', '-Command', ps_cmd],
            capture_output=True,
            text=True,
            timeout=60
        )
        selected = [line.strip() for line in res.stdout.splitlines() if line.strip()]
    except Exception as e:
        print(f"Native file dialog error: {e}")
        selected = []

    moved_count = 0
    if selected:
        for f in selected:
            src = Path(f)
            if src.is_file():
                dst = INPUT_DIR / src.name
                if safe_move_file(src, dst):
                    moved_count += 1
                    state.add_log(f"✂️ DIRECT CUT into input_media: {src.name}")
    return moved_count

def native_pick_and_cut_folder():
    """Opens native Windows folder dialog via isolated PowerShell and directly CUTS entire folder into input_media."""
    ps_cmd = (
        "Add-Type -AssemblyName System.Windows.Forms; "
        "$d = New-Object System.Windows.Forms.FolderBrowserDialog; "
        "$d.Description = 'Select Folder to CUT into input_media'; "
        "if ($d.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) { "
        "  Write-Output $d.SelectedPath "
        "}"
    )
    try:
        res = run_silent_cmd(
            ['powershell', '-Sta', '-NoProfile', '-Command', ps_cmd],
            capture_output=True,
            text=True,
            timeout=60
        )
        selected = res.stdout.strip()
    except Exception as e:
        print(f"Native folder dialog error: {e}")
        selected = ""

    moved_count = 0
    if selected and Path(selected).is_dir():
        src_dir = Path(selected)
        dest_dir = INPUT_DIR / src_dir.name
        all_exts = ('.mp4', '.mov', '.mkv', '.avi', '.webm', '.m4v', '.jpg', '.jpeg', '.png', '.webp')
        if not dest_dir.exists():
            try:
                shutil.move(str(src_dir), str(dest_dir))
                moved_count += 1
                state.add_log(f"✂️ DIRECT CUT folder into input_media: {src_dir.name}/")
            except Exception:
                shutil.copytree(str(src_dir), str(dest_dir))
                shutil.rmtree(str(src_dir), ignore_errors=True)
                moved_count += 1
        else:
            for item in list(src_dir.rglob("*")):
                if item.is_file() and item.suffix.lower() in all_exts:
                    rel = item.relative_to(src_dir)
                    target = dest_dir / rel
                    if safe_move_file(item, target):
                        moved_count += 1
            shutil.rmtree(str(src_dir), ignore_errors=True)
            state.add_log(f"✂️ DIRECT CUT folder contents into input_media: {src_dir.name}/")
    return moved_count

# Global App State
class EngineState:
    def __init__(self):
        self.is_processing = False
        self.stop_requested = False
        self.current_file = ""
        self.progress_current = 0
        self.progress_total = 0
        self.logs = []
        self.latest_result = None
        self.update_info = None
        self.lock = threading.Lock()

    def add_log(self, text):
        with self.lock:
            self.logs.append({"time": time.strftime("%H:%M:%S"), "message": text})
            if len(self.logs) > 500:
                self.logs.pop(0)

    def clear_logs(self):
        with self.lock:
            self.logs = []

    def get_status(self):
        with self.lock:
            return {
                "is_processing": self.is_processing,
                "stop_requested": self.stop_requested,
                "current_file": self.current_file,
                "progress_current": self.progress_current,
                "progress_total": self.progress_total,
                "latest_result": self.latest_result,
                "update_info": self.update_info,
                "logs": list(self.logs)
            }

state = EngineState()

def get_input_files():
    video_exts = ('.mp4', '.mov', '.mkv', '.avi', '.webm', '.m4v')
    photo_exts = ('.jpg', '.jpeg', '.png', '.webp', '.bmp')
    all_exts = video_exts + photo_exts
    files = []

    if INPUT_DIR.exists():
        for f in sorted(INPUT_DIR.rglob("*"), key=lambda x: str(x).lower()):
            if f.is_file() and f.suffix.lower() in all_exts:
                rel = str(f.relative_to(INPUT_DIR)).replace("\\", "/")
                files.append({
                    "name": rel,
                    "rel_path": rel,
                    "size_mb": round(f.stat().st_size / (1024 * 1024), 2),
                    "is_video": f.suffix.lower() in video_exts
                })
    return files

def process_worker(file_rel_paths, platform, direct_mode=False, upscale_4k=False):
    state.is_processing = True
    state.stop_requested = False
    state.progress_total = len(file_rel_paths)
    state.progress_current = 0

    try:
        cfg = load_config()
        raw_key = cfg.get("gemini_api_key", "").strip()

        rotator = GeminiKeyRotator(raw_key)
        if rotator.total_keys == 0:
            state.add_log("❌ Error: Gemini API Key not set. Please configure your API key in Settings.")
            return

        if rotator.total_keys > 1:
            state.add_log(f"🔑 Multi-Key Rotation Active: {rotator.total_keys} Gemini API keys loaded.")

        video_exts = ('.mp4', '.mov', '.mkv', '.avi', '.webm', '.m4v')

        for idx, rel_path in enumerate(file_rel_paths, 1):
            if state.stop_requested:
                state.add_log("🛑 Process stopped by user!")
                break

            media_path = INPUT_DIR / rel_path
            if not media_path.exists():
                continue

            state.progress_current = idx
            state.current_file = media_path.name
            is_video = media_path.suffix.lower() in video_exts

            # Set up parallel 4K render if enabled, is_video, and not in direct_mode
            render_thread = None
            render_status = {"done": False, "ok": False, "error": None}
            temp_4k_path = None

            if not direct_mode and is_video and upscale_4k:
                temp_4k_filename = f".render_4k_{int(time.time())}_{idx}.mp4"
                temp_4k_path = OUTPUT_DIR / temp_4k_filename

                def _bg_render(src_file=media_path, dst_file=temp_4k_path):
                    state.add_log(f"   ⚡ [Parallel GPU] 4K Ultra-HD Upscale render started in background...")
                    try:
                        ok = render_video_4k(src_file, dst_file, log_callback=lambda msg: state.add_log(f"   🎬 [4K Render]: {msg}"))
                        render_status["ok"] = ok
                    except Exception as rexc:
                        render_status["error"] = str(rexc)
                        render_status["ok"] = False
                    finally:
                        render_status["done"] = True

                render_thread = threading.Thread(target=_bg_render, daemon=True)
                render_thread.start()

            if direct_mode:
                state.add_log(f"⚡ [{idx}/{len(file_rel_paths)}] Direct Extract: {media_path.name}")
                state.add_log(f"   🛡️ Zero Modifications: Video will NOT be moved, cut, copied, or renamed.")
                state.add_log(f"   🛡️ Zero Disk Writes: No output folders or .txt files created on disk.")
                target_folder = None
                renamed_filename = media_path.name
            else:
                ext = media_path.suffix.lower()
                target_folder = OUTPUT_DIR
                target_folder.mkdir(parents=True, exist_ok=True)

                upscale_label = "4K Ultra-HD AI Upscale & " if (is_video and upscale_4k) else ""
                state.add_log(f"🎬 [{idx}/{len(file_rel_paths)}] Processing: {media_path.name}")
                state.add_log(f"   🎥 Video will be {upscale_label}renamed with Caption & Hashtags directly in output_media")

            uploaded_file = None
            ai_output = None
            active_client = None

            folder_hint = target_folder.name if target_folder else media_path.parent.name
            active_client, cur_k, tot_k = rotator.get_client() if rotator.total_keys > 0 else (None, 0, 0)
            api_key_to_use = rotator.keys[cur_k] if rotator.total_keys > 0 else None

            state.add_log(f"   🎬 Decoding video frames and analyzing content for '{media_path.name}'...")
            ai_output = local_video_seo.decode_video_with_gemini(
                media_path=media_path,
                client=active_client,
                api_key=api_key_to_use,
                platform=platform,
                folder_name=folder_hint,
                index=idx,
                log_callback=state.add_log
            )
            state.add_log(f"   ✨ Video decoding complete! Generated accurate Caption & 8+ Hashtags.")
            if False:
                upload_target, is_temp_preview = create_fast_video_preview(media_path)
                try:
                    state.add_log(f"   ⚡ Fast Cloud Upload: {media_path.name}...")
                    for up_att in range(1, 4):
                        if state.stop_requested:
                            break
                        try:
                            active_client, cur_k, tot_k = rotator.get_client()
                            uploaded_file = active_client.files.upload(file=str(upload_target))
                            state.add_log(f"   ⏳ Gemini Files API Active: {uploaded_file.name}")
                            break
                        except Exception as up_err:
                            u_str = str(up_err)
                            is_429 = "429" in u_str or "quota" in u_str.lower() or "resource_exhausted" in u_str.lower()
                            if is_429 and rotator.total_keys > 1 and rotator.rotate():
                                active_client, cur_k, tot_k = rotator.get_client()
                                state.add_log(f"   🔄 Quota limit (429) on upload. Switching to Key {cur_k + 1}/{tot_k}...")
                                time.sleep(1)
                                continue
                            elif is_429:
                                wait_sec = up_att * 8
                                state.add_log(f"   ⏳ Rate limit (429) on upload. Cooldown {wait_sec}s ({up_att}/3)...")
                                for _ in range(wait_sec):
                                    if state.stop_requested: break
                                    time.sleep(1)
                            else:
                                state.add_log(f"   [!] Upload retry notice: {u_str[:80]}")
                                time.sleep(1)

                    if not uploaded_file:
                        state.add_log(f"   ❌ Could not upload {media_path.name} to Gemini. Skipping file.")
                        if temp_4k_path and temp_4k_path.exists():
                            try:
                                temp_4k_path.unlink()
                            except Exception:
                                pass
                        continue

                    if is_video:
                        state.add_log("   👀 Gemini AI is watching and analyzing video & audio...")
                        wait_count = 0
                        while uploaded_file.state.name == "PROCESSING" and wait_count < 60:
                            if state.stop_requested:
                                break
                            time.sleep(0.8)
                            wait_count += 1
                            uploaded_file = active_client.files.get(name=uploaded_file.name)

                        if state.stop_requested:
                            try:
                                active_client.files.delete(name=uploaded_file.name)
                            except Exception:
                                pass
                            state.add_log("🛑 Analysis cancelled during video processing!")
                            if temp_4k_path and temp_4k_path.exists():
                                try:
                                    temp_4k_path.unlink()
                                except Exception:
                                    pass
                            break

                        if uploaded_file.state.name == "FAILED":
                            state.add_log(f"   [!] Gemini Video Processing Failed: {uploaded_file.error}")
                            if temp_4k_path and temp_4k_path.exists():
                                try:
                                    temp_4k_path.unlink()
                                except Exception:
                                    pass
                            continue

                    if state.stop_requested:
                        try:
                            active_client.files.delete(name=uploaded_file.name)
                        except Exception:
                            pass
                        if temp_4k_path and temp_4k_path.exists():
                            try:
                                temp_4k_path.unlink()
                            except Exception:
                                pass
                        state.add_log("🛑 Analysis cancelled by user!")
                        break

                    prompt = f"""Watch and listen to this entire attached video. Analyze all dialogue/audio, visual cues, humor, action, and key emotion.
Generate a viral, engaging social media post for {platform.upper()} strictly in 100% FLUENT ENGLISH.

FORMAT REQUIREMENTS:
Provide ONLY the story-driven caption followed directly by hashtags.
Do NOT include ANY section titles, labels, or prefixes (Do NOT write '🎯 HOOK:', '📌 CAPTION:', '🏷️ HASHTAGS:', 'Caption:', 'Hook:', etc.).

CRITICAL HASHTAGS RULE (MINIMUM 7-8 VIRAL HASHTAGS):
You MUST ALWAYS generate a minimum of 7 to 8 viral and relevant hashtags (e.g. 7 to 10 hashtags total).
Always include #MustWatch, #FYP, #Viral, plus 4-6 specific viral and niche hashtags (e.g. #Trending #Reels #ExplorePage #VideoOfTheDay #ViralReels #ForYouPage).
Never output fewer than 7 hashtags!

EXACT FORMAT TO FOLLOW:
[Engaging, 1-2 sentence story-driven caption strictly in fluent English describing the key moment, emotion, humor, or situation with appropriate emojis]

#ContentTag #MustWatch #FYP #Viral #Trending #Reels #ExplorePage #ViralReels

EXAMPLE:
She walks in with her paperwork and family confrontation explodes! 😳📄 Accusations fly and tempers flare. 👀🔥 #FamilyDrama #MustWatch #FYP #Viral #Trending #ViralReels #ExplorePage #ForYouPage

CRITICAL RULES:
- EVERYTHING MUST be written strictly in 100% FLUENT ENGLISH ONLY.
- Regardless of the spoken language or dialogue in the video, write EVERYTHING strictly in 100% FLUENT ENGLISH.
- Absolutely NO section labels, headers, or markdown titles.
- Output ONLY the clean caption followed immediately by minimum 7-8 hashtags."""

                    state.add_log(f"   🤖 Gemini AI generating Caption & 7-8+ Hashtags for {platform.upper()}...")
                    for model_name in ACTIVE_MODELS:
                        if state.stop_requested or ai_output:
                            break
                        for retry_round in range(1, 4):
                            if state.stop_requested or ai_output:
                                break
                            try:
                                client_to_use, cur_k, tot_k = rotator.get_client()
                                resp = client_to_use.models.generate_content(
                                    model=model_name,
                                    contents=[uploaded_file, prompt]
                                )
                                if resp and resp.text:
                                    ai_output = clean_ai_output(resp.text)
                                    state.add_log(f"   ✅ Gemini ({model_name}) generated pure English Caption & Hashtags!")
                                    break
                            except Exception as merr:
                                err_str = str(merr)
                                is_429 = "429" in err_str or "quota" in err_str.lower() or "resource_exhausted" in err_str.lower()
                                if is_429:
                                    if rotator.total_keys > 1 and rotator.rotate():
                                        client_to_use, cur_k, tot_k = rotator.get_client()
                                        state.add_log(f"   🔄 Quota limit (429) on {model_name}. Switching to API Key {cur_k + 1}/{tot_k}...")
                                        time.sleep(1.5)
                                        continue
                                    else:
                                        state.add_log(f"   ⚡ Rate limit (429) on Gemini. Instantly switching to Smart Video SEO Engine...")
                                        folder_hint = target_folder.name if target_folder else media_path.parent.name
                                        ai_output = local_video_seo.generate_local_caption_and_hashtags(
                                            media_path=media_path,
                                            folder_name=folder_hint,
                                            index=idx,
                                            platform=platform
                                        )
                                        break
                                elif "503" in err_str or "404" in err_str or "demand" in err_str.lower():
                                    time.sleep(1)
                                    break
                                else:
                                    state.add_log(f"   [!] Model notice ({model_name}): {err_str[:80]}")
                                    break

                        if ai_output:
                            break

                except Exception as e:
                    state.add_log(f"   [!] Gemini Notice: {e}")
                finally:
                    if is_temp_preview and upload_target.exists():
                        try:
                            upload_target.unlink()
                        except Exception:
                            pass
                    if uploaded_file and active_client:
                        try:
                            active_client.files.delete(name=uploaded_file.name)
                        except Exception:
                            pass
                    uploaded_file = None
                    import gc
                    gc.collect()
                    time.sleep(0.1)

            # Video-matched local SEO if Gemini was not available or rate limited
            if not ai_output:
                folder_hint = target_folder.name if target_folder else media_path.parent.name
                ai_output = local_video_seo.generate_local_caption_and_hashtags(
                    media_path=media_path,
                    folder_name=folder_hint,
                    index=idx,
                    platform=platform
                )
                state.add_log(f"   ✨ Generated video-matched Caption & 8+ Hashtags for: {media_path.name}")

            if state.stop_requested:
                if temp_4k_path and temp_4k_path.exists():
                    try:
                        temp_4k_path.unlink()
                    except Exception:
                        pass
                state.add_log("🛑 Analysis stopped by user! No further files will be moved.")
                break

            # If 4K render was running in background, wait for it to finish
            if render_thread and render_thread.is_alive():
                state.add_log("   ⏳ Finalizing parallel 4K render on GPU...")
                render_thread.join(timeout=300)

            if direct_mode:
                state.latest_result = {
                    "folder": "Direct Extract (Zero File Changes)",
                    "video_file": media_path.name,
                    "txt_file": "Direct On-Screen Display",
                    "content": ai_output
                }
                state.add_log(f"   ✨ Direct Extract Complete for: '{media_path.name}' (Original 100% untouched)")
            else:
                # Use .mp4 if 4K rendered successfully, otherwise original ext
                output_ext = ".mp4" if (render_status.get("ok") and temp_4k_path and temp_4k_path.exists() and temp_4k_path.stat().st_size > 0) else ext

                # Generate video filename directly from AI Caption + Hashtags (zero .txt file)
                renamed_filename = generate_video_filename(ai_output, output_ext, target_folder, fallback_stem=media_path.stem)
                target_media = target_folder / renamed_filename

                import gc
                gc.collect()
                time.sleep(0.3)

                if render_status.get("ok") and temp_4k_path and temp_4k_path.exists() and temp_4k_path.stat().st_size > 0:
                    # Move 4K rendered video to target_media in output_media
                    safe_move_file(temp_4k_path, target_media)
                    state.add_log(f"   ✨ 4K Ultra-HD Video successfully saved to output_media!")
                    # Cleanly CUT / delete original from input_media
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
                    # Fallback: strictly CUT original media from input_media into output_media
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

                # Save 100% identical matching .txt package right next to the video
                try:
                    txt_file = target_media.with_suffix('.txt')
                    with open(txt_file, 'w', encoding='utf-8') as f:
                        f.write(ai_output.strip() + '\n')
                    state.add_log(f"   📝 Full matching Caption & Hashtags saved: {txt_file.name}")
                except Exception as te:
                    pass

                state.latest_result = {
                    "folder": target_folder.name if target_folder else "output_media",
                    "video_file": renamed_filename,
                    "txt_file": f"{target_media.stem}.txt",
                    "content": ai_output
                }

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

                state.add_log(f"   ✂️  CUT & RENAMED ➔ {renamed_filename}")

                state.latest_result = {
                    "folder": "",
                    "video_file": renamed_filename,
                    "txt_file": "",
                    "content": ai_output
                }

                # Polite pacing delay between batch videos to protect RPM quota
                if idx < len(file_rel_paths) and not state.stop_requested:
                    time.sleep(2.0)

        if not state.stop_requested:
            state.add_log(f"🎉 Success! Finished processing {len(file_rel_paths)} video(s).")
    except Exception as exc:
        state.add_log(f"❌ Unexpected processing error: {exc}")
    finally:
        state.is_processing = False
        state.stop_requested = False

def direct_process_worker(media_path, original_filename, platform, is_temp=False):
    """
    Directly extracts Caption & Hashtags via Gemini Vision AI
    WITHOUT cutting, copying, renaming, moving, or writing any files to disk.
    The original file remains 100% untouched.
    """
    state.is_processing = True
    state.stop_requested = False
    state.progress_total = 1
    state.progress_current = 1
    state.current_file = original_filename

    state.add_log(f"⚡ [Direct Extract Mode]: Analyzing '{original_filename}' with Gemini Vision (Zero File Modifications)...")
    state.add_log(f"   ℹ️ Rule: Original video will NOT be moved, cut, copied, or renamed. No output files will be saved.")

    try:
        cfg = load_config()
        raw_key = cfg.get("gemini_api_key", "").strip()
        rotator = GeminiKeyRotator(raw_key)
        platform = cfg.get("target_platform", "facebook")
        active_client, cur_k, tot_k = rotator.get_client() if rotator.total_keys > 0 else (None, 0, 0)
        api_key_to_use = rotator.keys[cur_k] if rotator.total_keys > 0 else None
        state.add_log(f"   🎬 Decoding video frames and analyzing content for '{original_filename}'...")
        ai_output = local_video_seo.decode_video_with_gemini(
            media_path=media_path,
            client=active_client,
            api_key=api_key_to_use,
            platform=platform,
            folder_name=media_path.parent.name,
            index=1,
            log_callback=state.add_log
        )
        state.latest_result = {
            "folder": "Direct Extract (Zero File Changes)",
            "video_file": original_filename,
            "txt_file": "Direct On-Screen Display",
            "content": ai_output
        }
        state.add_log(f"   ✨ Direct Extract Complete: '{original_filename}'")
        return

        video_exts = ('.mp4', '.mov', '.mkv', '.avi', '.webm', '.m4v')
        is_video = Path(original_filename).suffix.lower() in video_exts

        uploaded_file = None
        ai_output = None
        active_client = None
        upload_target, is_temp_preview = create_fast_video_preview(media_path)

        try:
            state.add_log(f"   ⚡ Fast Cloud Upload: {original_filename}...")
            for up_att in range(1, 4):
                if state.stop_requested:
                    break
                try:
                    active_client, cur_k, tot_k = rotator.get_client()
                    uploaded_file = active_client.files.upload(file=str(upload_target))
                    state.add_log(f"   ⏳ Gemini Cloud Stream Active: {uploaded_file.name}")
                    break
                except Exception as up_err:
                    u_str = str(up_err)
                    is_429 = "429" in u_str or "quota" in u_str.lower() or "resource_exhausted" in u_str.lower()
                    if is_429 and rotator.total_keys > 1 and rotator.rotate():
                        active_client, cur_k, tot_k = rotator.get_client()
                        state.add_log(f"   🔄 Quota limit (429) on upload. Switching to Key {cur_k + 1}/{tot_k}...")
                        time.sleep(1)
                        continue
                    elif is_429:
                        wait_sec = up_att * 8
                        state.add_log(f"   ⏳ Rate limit (429) on upload. Cooldown {wait_sec}s ({up_att}/3)...")
                        for _ in range(wait_sec):
                            if state.stop_requested: break
                            time.sleep(1)
                    else:
                        state.add_log(f"   [!] Upload retry notice: {u_str[:80]}")
            if is_temp_preview and upload_target.exists():
                try:
                    upload_target.unlink()
                except Exception:
                    pass

            if not uploaded_file:
                state.add_log(f"   ❌ Upload failed for {original_filename}.")
                return

            if is_video:
                state.add_log("   👀 Gemini AI is watching and analyzing video & audio directly...")
                wait_count = 0
                while uploaded_file.state.name == "PROCESSING" and wait_count < 60:
                    if state.stop_requested:
                        break
                    time.sleep(0.8)
                    wait_count += 1
                    uploaded_file = active_client.files.get(name=uploaded_file.name)

                if uploaded_file.state.name == "FAILED":
                    state.add_log(f"   [!] Gemini Video Processing Failed: {uploaded_file.error}")
                    return

            if not state.stop_requested:
                prompt = f"""Watch and listen to this entire attached video. Analyze all dialogue/audio, visual cues, humor, action, and key emotion.
Generate a viral, engaging social media post for {platform.upper()} strictly in 100% FLUENT ENGLISH.

FORMAT REQUIREMENTS:
Provide ONLY the story-driven caption followed directly by hashtags.
Do NOT include ANY section titles, labels, or prefixes (Do NOT write '🎯 HOOK:', '📌 CAPTION:', '🏷️ HASHTAGS:', 'Caption:', 'Hook:', etc.).

CRITICAL HASHTAGS RULE (MINIMUM 7-8 VIRAL HASHTAGS):
You MUST ALWAYS generate a minimum of 7 to 8 viral and relevant hashtags (e.g. 7 to 10 hashtags total).
Always include #MustWatch, #FYP, #Viral, plus 4-6 specific viral and niche hashtags (e.g. #Trending #Reels #ExplorePage #VideoOfTheDay #ViralReels #ForYouPage).
Never output fewer than 7 hashtags!

EXACT FORMAT TO FOLLOW:
[Engaging, 1-2 sentence story-driven caption strictly in fluent English describing the key moment, emotion, humor, or situation with appropriate emojis]

#ContentTag #MustWatch #FYP #Viral #Trending #Reels #ExplorePage #ViralReels

EXAMPLE:
She walks in with her paperwork and family confrontation explodes! 😳📄 Accusations fly and tempers flare. 👀🔥 #FamilyDrama #MustWatch #FYP #Viral #Trending #ViralReels #ExplorePage #ForYouPage

CRITICAL RULES:
- EVERYTHING MUST be written strictly in 100% FLUENT ENGLISH ONLY.
- Regardless of the spoken language or dialogue in the video, write EVERYTHING strictly in 100% FLUENT ENGLISH.
- Absolutely NO section labels, headers, or markdown titles.
- Output ONLY the clean caption followed immediately by minimum 7-8 hashtags."""

                state.add_log(f"   🤖 Gemini AI generating pure English Caption & Hashtags for {platform.upper()}...")
                for model_name in ACTIVE_MODELS:
                    if state.stop_requested or ai_output:
                        break
                    for retry_round in range(1, 4):
                        if state.stop_requested or ai_output:
                            break
                        try:
                            client_to_use, cur_k, tot_k = rotator.get_client()
                            resp = client_to_use.models.generate_content(
                                model=model_name,
                                contents=[uploaded_file, prompt]
                            )
                            if resp and resp.text:
                                ai_output = clean_ai_output(resp.text)
                                state.add_log(f"   ✅ Gemini ({model_name}) generated pure English Caption & Hashtags!")
                                break
                        except Exception as merr:
                            err_str = str(merr)
                            is_429 = "429" in err_str or "quota" in err_str.lower() or "resource_exhausted" in err_str.lower()
                            if is_429:
                                if rotator.total_keys > 1 and rotator.rotate():
                                    client_to_use, cur_k, tot_k = rotator.get_client()
                                    state.add_log(f"   🔄 Quota limit (429) on {model_name}. Switching to API Key {cur_k + 1}/{tot_k}...")
                                    time.sleep(1.5)
                                    continue
                                else:
                                    wait_sec = retry_round * 15
                                    state.add_log(f"   ⏳ Rate limit (429) active. Pausing {wait_sec}s for quota cooldown ({retry_round}/3)...")
                                    for _ in range(wait_sec):
                                        if state.stop_requested: break
                                        time.sleep(1)
                                    continue
                            elif "503" in err_str or "404" in err_str or "demand" in err_str.lower():
                                time.sleep(1.5)
                                break
                            else:
                                state.add_log(f"   [!] Model notice ({model_name}): {err_str[:80]}")
                                break

        finally:
            if uploaded_file and active_client:
                try:
                    active_client.files.delete(name=uploaded_file.name)
                except Exception:
                    pass
            if is_temp:
                try:
                    if os.path.exists(media_path):
                        os.unlink(media_path)
                except Exception:
                    pass

        if not ai_output:
            ai_output = f"""An unexpected and emotional moment caught on camera! Watch closely as the story unfolds with the biggest smile. What would your reaction be in this situation? Let us know your thoughts in the comments below! 👇💬❤️

#Viral #Trending #MustWatch #VideoOfTheDay #StoryTime #ExplorePage #FYP #Reels #CuteAnimals #WholesomeMoments #FunnyReels #ViralReels #{platform.capitalize()}Watch #Entertainment"""
        else:
            ai_output = clean_ai_output(ai_output)

        state.latest_result = {
            "folder": "Direct Extract (Zero File Changes)",
            "video_file": original_filename,
            "txt_file": "Direct On-Screen Display",
            "content": ai_output
        }
        state.add_log(f"🎉 Success! Extracted Caption & Hashtags for '{original_filename}' with ZERO file moves or saves.")
        state.add_log(f"📋 Click 'Copy All' to copy your ready-to-post English package.")
    except Exception as exc:
        state.add_log(f"❌ Direct extract error: {exc}")
    finally:
        state.is_processing = False
        state.stop_requested = False

class LustreHTTPHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WORKSPACE_DIR), **kwargs)

    def translate_path(self, path):
        # First check in WORKSPACE_DIR
        local_path = super().translate_path(path)
        if os.path.exists(local_path):
            return local_path
        # Fallback to BUNDLE_DIR if running from PyInstaller frozen bundle
        try:
            rel = os.path.relpath(local_path, str(WORKSPACE_DIR))
            bundle_path = BUNDLE_DIR / rel
            if bundle_path.exists():
                return str(bundle_path)
        except Exception:
            pass
        return local_path
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()

    def log_message(self, format, *args):
        try:
            if sys.stderr and not sys.stderr.closed:
                super().log_message(format, *args)
        except Exception:
            pass

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/status":
            self.send_json(state.get_status())
        elif path == "/api/files":
            self.send_json({"files": get_input_files()})
        elif path == "/api/config":
            self.send_json(load_config())
        elif path == "/api/update_status":
            info = auto_updater.check_for_updates()
            state.update_info = info
            self.send_json(info)
        elif path == "/api/open_input":
            ok = open_directory_in_explorer(INPUT_DIR)
            self.send_json({"ok": ok, "message": "Input folder opened"})
        elif path == "/api/open_output":
            ok = open_directory_in_explorer(OUTPUT_DIR)
            self.send_json({"ok": ok, "message": "Output folder opened"})
        else:
            if path == "/" or path == "":
                self.path = "/index.html"
            super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        content_len = int(self.headers.get('Content-Length', 0))

        if path == "/api/upload":
            try:
                rel_raw = self.headers.get('X-Relative-Path', '')
                if not rel_raw:
                    rel_raw = self.headers.get('X-File-Name', 'uploaded_video.mp4')
                import urllib.parse
                rel_path = urllib.parse.unquote(rel_raw).replace('\\', '/').strip('/')

                # Strip Windows drive letters (e.g. C:, D:)
                if ':' in rel_path:
                    rel_path = rel_path.split(':', 1)[-1].lstrip('/')

                # Clean path segments while preserving legitimate names with double dots like "video..mp4"
                clean_parts = []
                for part in rel_path.split('/'):
                    p = part.strip()
                    if not p or p == '.':
                        continue
                    if p == '..':
                        continue  # skip directory traversal token
                    # Strip unsafe filesystem characters
                    p = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', p).strip('. ')
                    if p:
                        clean_parts.append(p)

                if not clean_parts:
                    fname = self.headers.get('X-File-Name', 'uploaded_video.mp4')
                    fname = urllib.parse.unquote(fname).replace('\\', '/').split('/')[-1]
                    fname = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', fname).strip('. ') or 'uploaded_video.mp4'
                    clean_parts = [fname]

                dest_path = INPUT_DIR.joinpath(*clean_parts)
                # Ensure destination is strictly inside INPUT_DIR
                try:
                    dest_path.resolve().relative_to(INPUT_DIR.resolve())
                except ValueError:
                    dest_path = INPUT_DIR / clean_parts[-1]

                dest_path.parent.mkdir(parents=True, exist_ok=True)

                if content_len <= 0:
                    self.send_json({"error": "Empty file content received"}, status=400)
                    return

                remaining = content_len
                chunk_size = 2 * 1024 * 1024  # 2MB chunks for ultra-fast local streaming
                with open(dest_path, "wb") as f:
                    while remaining > 0:
                        read_bytes = min(remaining, chunk_size)
                        chunk = self.rfile.read(read_bytes)
                        if not chunk:
                            break
                        f.write(chunk)
                        remaining -= len(chunk)

                size_mb = dest_path.stat().st_size / (1024 * 1024)
                rel_display = str(dest_path.relative_to(INPUT_DIR)).replace('\\', '/')
                state.add_log(f"📥 Video Uploaded: {rel_display} ({size_mb:.1f} MB)")
                self.send_json({"ok": True, "saved": rel_display, "size_mb": round(size_mb, 2)})
            except Exception as e:
                state.add_log(f"❌ Upload Error: {e}")
                self.send_json({"error": str(e)}, status=500)
            return

        if path == "/api/direct_extract_upload":
            if state.is_processing:
                self.send_json({"error": "AI is already processing a video"}, status=400)
                return
            filename = self.headers.get('X-File-Name', 'video.mp4')
            import urllib.parse
            filename = urllib.parse.unquote(filename).replace('\\', '/').split('/')[-1]
            platform = self.headers.get('X-Platform', 'facebook').lower()

            import tempfile
            temp_dir = Path(tempfile.gettempdir())
            temp_path = temp_dir / f"lustre_direct_{int(time.time())}_{filename}"

            remaining = content_len
            chunk_size = 64 * 1024
            with open(temp_path, "wb") as f:
                while remaining > 0:
                    read_bytes = min(remaining, chunk_size)
                    chunk = self.rfile.read(read_bytes)
                    if not chunk:
                        break
                    f.write(chunk)
                    remaining -= len(chunk)

            size_mb = temp_path.stat().st_size / (1024 * 1024)
            state.add_log(f"⚡ Direct Extract Upload: Received {filename} ({size_mb:.1f} MB)")
            threading.Thread(target=direct_process_worker, args=(temp_path, filename, platform, True), daemon=True).start()
            self.send_json({"ok": True, "message": f"Direct AI analysis started for {filename}"})
            return

        body = self.rfile.read(content_len).decode('utf-8') if content_len > 0 else "{}"
        try:
            data = json.loads(body)
        except Exception:
            data = {}

        if path == "/api/direct_extract_selected":
            if state.is_processing:
                self.send_json({"error": "AI is already processing a video"}, status=400)
                return
            rel_path = data.get("file", "").strip()
            platform = data.get("platform", "facebook")
            if not rel_path:
                self.send_json({"error": "No file specified"}, status=400)
                return
            media_path = INPUT_DIR / rel_path
            if not media_path.exists():
                self.send_json({"error": f"File not found: {rel_path}"}, status=404)
                return
            threading.Thread(target=direct_process_worker, args=(media_path, media_path.name, platform, False), daemon=True).start()
            self.send_json({"ok": True, "message": f"Direct AI extraction started for {media_path.name}"})

        elif path == "/api/process":
            if state.is_processing:
                self.send_json({"error": "Already processing"}, status=400)
                return
            
            files = data.get("files", [])
            platform = data.get("platform", "facebook")
            direct_mode = bool(data.get("direct_mode", False))
            upscale_4k = bool(data.get("upscale_4k", load_config().get("upscale_4k", False)))

            if not files:
                all_files = [f["rel_path"] for f in get_input_files()]
                files = all_files

            if not files:
                self.send_json({"error": "No files found in input_media"}, status=400)
                return

            threading.Thread(target=process_worker, args=(files, platform, direct_mode, upscale_4k), daemon=True).start()
            mode_desc = "Direct Extract (No Move/Save)" if direct_mode else ("4K Process & Rename" if upscale_4k else "Process & Rename")
            self.send_json({"message": f"Started {mode_desc} for {len(files)} file(s)"})

        elif path == "/api/stop":
            if state.is_processing:
                state.stop_requested = True
                state.add_log("⚠️ Stop request received from Web UI...")
                self.send_json({"message": "Stop requested"})
            else:
                self.send_json({"message": "Not processing"})

        elif path == "/api/config":
            cfg = load_config()
            cfg.update(data)
            save_config(cfg)
            self.send_json({"message": "Config saved", "config": cfg})

        elif path == "/api/open_output":
            ok = open_directory_in_explorer(OUTPUT_DIR)
            self.send_json({"ok": ok, "message": "Output folder opened"})

        elif path == "/api/open_input":
            ok = open_directory_in_explorer(INPUT_DIR)
            self.send_json({"ok": ok, "message": "Input folder opened"})

        elif path in ("/api/clear_result", "/api/reset_all", "/api/reset_stats"):
            with state.lock:
                state.latest_result = None
                state.progress_current = 0
                state.progress_total = 0
                state.current_file = ""
                state.stop_requested = False
                state.is_processing = False
            self.send_json({"ok": True, "message": "Full engine state & results reset"})

        elif path == "/api/delete_file":
            try:
                file_rel = data.get("file", "").strip()
                if not file_rel:
                    self.send_json({"error": "No file specified"}, status=400)
                    return
                target_path = (INPUT_DIR / file_rel).resolve()
                if not str(target_path).startswith(str(INPUT_DIR.resolve())):
                    self.send_json({"error": "Unauthorized path"}, status=403)
                    return
                if not target_path.exists():
                    self.send_json({"ok": True, "message": "File already removed"})
                    return
                if target_path.is_file():
                    fname = target_path.name
                    target_path.unlink()
                    state.add_log(f"🗑️ Deleted file from input_media: {fname}")
                    try:
                        if target_path.parent != INPUT_DIR.resolve() and not any(target_path.parent.iterdir()):
                            target_path.parent.rmdir()
                    except Exception:
                        pass
                    self.send_json({"ok": True, "message": f"Deleted {fname}"})
                else:
                    self.send_json({"error": "Target is not a file"}, status=400)
            except Exception as e:
                self.send_json({"error": str(e)}, status=500)

        elif path == "/api/delete_all":
            try:
                count = 0
                for item in list(INPUT_DIR.glob("**/*")):
                    if item.is_file():
                        try:
                            item.unlink()
                            count += 1
                        except Exception:
                            pass
                for d in list(INPUT_DIR.glob("**/*")):
                    if d.is_dir():
                        try:
                            if not any(d.iterdir()):
                                d.rmdir()
                        except Exception:
                            pass
                state.add_log(f"🗑️ Deleted all {count} file(s) from input_media.")
                self.send_json({"ok": True, "count": count, "message": f"Deleted {count} file(s)"})
            except Exception as e:
                self.send_json({"error": str(e)}, status=500)

        elif path == "/api/pick_and_cut_files":
            try:
                count = native_pick_and_cut_files()
                self.send_json({"ok": True, "count": count, "message": f"Directly CUT {count} video(s) into input_media"})
            except Exception as e:
                self.send_json({"error": str(e)}, status=500)

        elif path == "/api/pick_and_cut_folder":
            try:
                count = native_pick_and_cut_folder()
                self.send_json({"ok": True, "count": count, "message": f"Directly CUT folder with {count} video(s) into input_media"})
            except Exception as e:
                self.send_json({"error": str(e)}, status=500)

        elif path == "/api/clear_logs":
            state.clear_logs()
            self.send_json({"ok": True, "message": "Logs cleared"})

        elif path == "/api/check_update":
            info = auto_updater.check_for_updates()
            state.update_info = info
            self.send_json(info)

        elif path == "/api/perform_update":
            result = auto_updater.perform_update()
            if result.get("ok"):
                state.add_log(f"🎉 Auto-Update: {result.get('message')}")
            else:
                state.add_log(f"❌ Auto-Update Error: {result.get('error')}")
            self.send_json(result)

        elif path == "/api/perform_push":
            commit_msg = data.get("commit_message", "").strip() or None
            result = auto_updater.perform_push(commit_msg)
            if result.get("ok"):
                state.add_log(f"🚀 GitHub Push: {result.get('message')}")
            else:
                state.add_log(f"❌ GitHub Push Error: {result.get('error')}")
            self.send_json(result)

        elif path == "/api/configure_git":
            remote_url = data.get("remote_url", "").strip()
            branch = data.get("branch", "main").strip()
            result = auto_updater.initialize_git_remote(remote_url, branch)
            self.send_json(result)

        else:
            self.send_json({"error": "Not Found"}, status=404)

    def send_json(self, data, status=200):
        response = json.dumps(data).encode('utf-8')
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(response)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

import socket

def free_port(port):
    """If port is occupied by an orphaned process on Windows, terminate that process silently without any console popup."""
    if not sys.platform.startswith('win'):
        return
    try:
        # First test if port is in use using pure socket (zero subprocess overhead/flicker)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.1)
            if s.connect_ex(('127.0.0.1', port)) != 0:
                return  # Port is already free, do nothing
    except Exception:
        pass

    try:
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        creationflags = getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000)

        res = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True, text=True, timeout=5,
            startupinfo=startupinfo,
            creationflags=creationflags,
            stdin=subprocess.DEVNULL
        )
        for line in res.stdout.splitlines():
            if f":{port}" in line and "LISTENING" in line:
                parts = line.strip().split()
                pid = parts[-1]
                if pid and pid.isdigit() and int(pid) != os.getpid():
                    subprocess.run(
                        ["taskkill", "/F", "/PID", pid],
                        capture_output=True, timeout=5,
                        startupinfo=startupinfo,
                        creationflags=creationflags,
                        stdin=subprocess.DEVNULL
                    )
        time.sleep(0.3)
    except Exception:
        pass

def run_server(port=5050, open_browser=True):
    free_port(port)
    ThreadingHTTPServer.allow_reuse_address = True
    server = None
    for attempt in range(3):
        try:
            server = ThreadingHTTPServer(("0.0.0.0", port), LustreHTTPHandler)
            break
        except OSError:
            try:
                server = ThreadingHTTPServer(("127.0.0.1", port), LustreHTTPHandler)
                break
            except OSError:
                if attempt == 0:
                    free_port(port)
                    time.sleep(1.0)
                else:
                    port += 1

    if not server:
        print(f"❌ Could not bind server to port {port}")
        return

    url = f"http://localhost:{port}"
    print("=" * 64)
    print(f"✨ Lustre Separator Web Server is running at: {url}")
    print("=" * 64)

    if open_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Web Server...")
        server.shutdown()

if __name__ == "__main__":
    env_port = os.environ.get("PORT")
    port = int(env_port) if env_port else 5050
    open_browser = False if env_port else True
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            if arg == "--no-browser":
                open_browser = False
            else:
                try:
                    port = int(arg)
                except Exception:
                    pass
    run_server(port=port, open_browser=open_browser)
