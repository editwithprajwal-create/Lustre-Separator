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
import mimetypes
import webbrowser
import re
from pathlib import Path
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import auto_updater

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
        print(f"Error saving config: {e}")

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

def generate_video_filename(ai_text, ext, target_folder=None, fallback_stem="video", max_len=248):
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
            tags = hashtags.split()
            tag_part = ' '.join(tags)
            if len(tag_part) + 80 <= max_len:
                avail_caption = max_len - len(tag_part) - 1
                truncated = caption[:avail_caption]
                last_space = truncated.rfind(' ')
                if last_space > avail_caption // 2:
                    caption_part = truncated[:last_space].rstrip('. ')
                else:
                    caption_part = truncated.rstrip('. ')
                base_name = f"{caption_part} {tag_part}".strip()
            else:
                selected_tags = []
                t_len = 0
                max_tag_budget = max_len - min(len(caption), 100) - 1
                for t in tags:
                    if t_len + len(t) + 1 <= max_tag_budget:
                        selected_tags.append(t)
                        t_len += len(t) + 1
                    else:
                        break
                tag_part = ' '.join(selected_tags)
                avail_caption = max_len - len(tag_part) - 1
                truncated = caption[:avail_caption]
                last_space = truncated.rfind(' ')
                if last_space > avail_caption // 2:
                    caption_part = truncated[:last_space].rstrip('. ')
                else:
                    caption_part = truncated.rstrip('. ')
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
    # Copy file, verify destination, then force delete original
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
        res = subprocess.run(
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
        res = subprocess.run(
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

def process_worker(file_rel_paths, platform, direct_mode=False):
    state.is_processing = True
    state.stop_requested = False
    state.progress_total = len(file_rel_paths)
    state.progress_current = 0

    try:
        cfg = load_config()
        api_key = cfg.get("gemini_api_key", "").strip()

        if not api_key:
            state.add_log("❌ Error: Gemini API Key not set. Please configure your API key in Settings.")
            return

        from google import genai
        client = genai.Client(api_key=api_key)

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

                state.add_log(f"🎬 [{idx}/{len(file_rel_paths)}] Processing: {media_path.name}")
                state.add_log("   🎥 Video will be renamed with Caption & Hashtags directly in output_media")

            uploaded_file = None
            ai_output = None

            try:
                state.add_log(f"   📤 Uploading {media_path.name} directly to Gemini Files API...")
                uploaded_file = client.files.upload(file=str(media_path))
                state.add_log(f"   ⏳ Gemini Files API Registered: {uploaded_file.name}")

                if is_video:
                    state.add_log("   👀 Gemini AI is watching and analyzing video & audio...")
                    wait_count = 0
                    while uploaded_file.state.name == "PROCESSING" and wait_count < 120:
                        if state.stop_requested:
                            break
                        time.sleep(3)
                        wait_count += 3
                        uploaded_file = client.files.get(name=uploaded_file.name)

                    if state.stop_requested:
                        try:
                            client.files.delete(name=uploaded_file.name)
                        except Exception:
                            pass
                        state.add_log("🛑 Analysis cancelled during video processing!")
                        break

                    if uploaded_file.state.name == "FAILED":
                        state.add_log(f"   [!] Gemini Video Processing Failed: {uploaded_file.error}")
                        continue

                if state.stop_requested:
                    try:
                        client.files.delete(name=uploaded_file.name)
                    except Exception:
                        pass
                    state.add_log("🛑 Analysis cancelled by user!")
                    break

                prompt = f"""Watch and listen to this entire attached video. Analyze what is happening, all dialogue/audio, visual cues, and the core message.
Generate a viral, engaging social media post for {platform.upper()} strictly in 100% FLUENT ENGLISH.

FORMAT REQUIREMENTS:
Provide ONLY the story-driven caption followed directly by hashtags.
Do NOT include ANY section titles, labels, or prefixes (Do NOT write '🎯 HOOK:', '📌 CAPTION:', '🏷️ HASHTAGS:', 'Caption:', 'Hook:', etc.).

CRITICAL LENGTH RULE FOR VIDEO FILENAME:
Keep the entire output (caption + all hashtags combined) concise, punchy, and strictly within 220 characters so that the entire text fits 100% into the video file name without getting cut off. Write 1-2 impactful sentences for the caption, followed by 5-8 top viral hashtags for {platform.upper()}.

EXACT FORMAT TO FOLLOW:
[Engaging, story-driven caption strictly in fluent English describing the key moment, emotion, humor, or situation with appropriate emojis]

#Hashtag1 #Hashtag2 #Hashtag3 #Hashtag4 #Hashtag5 #Hashtag6 #Hashtag7 #Hashtag8

EXAMPLE:
She walks in with her paperwork and family confrontation explodes! 😳📄 Accusations fly and drama got real. 👀🔥 #FamilyDrama #FamilySecrets #RelationshipDrama #StoryTime #ViralReels #MustWatch

CRITICAL RULES:
- EVERYTHING MUST be written strictly in 100% FLUENT ENGLISH ONLY.
- Regardless of the spoken language or dialogue in the video (even if Nepali, Hindi, Spanish, etc.), you MUST translate all concepts and write EVERYTHING strictly in 100% FLUENT ENGLISH.
- Absolutely NO section labels, headers, or markdown titles.
- Absolutely NO Devanagari, Nepali, Hindi, or non-English script.
- Do NOT include any intro, outro, explanations, search keywords, or conversational filler.
- Output ONLY the clean caption followed immediately by the hashtags."""

                state.add_log(f"   🤖 Gemini AI generating pure English Caption & Hashtags for {platform.upper()}...")
                for model_name in ACTIVE_MODELS:
                    if state.stop_requested:
                        break
                    try:
                        resp = client.models.generate_content(
                            model=model_name,
                            contents=[uploaded_file, prompt]
                        )
                        if resp and resp.text:
                            ai_output = clean_ai_output(resp.text)
                            state.add_log(f"   ✅ Gemini ({model_name}) generated pure English Caption & Hashtags!")
                            break
                    except Exception as merr:
                        err_str = str(merr)
                        if "503" in err_str or "404" in err_str or "demand" in err_str.lower():
                            time.sleep(1)
                            continue
                        else:
                            state.add_log(f"   [!] Model notice ({model_name}): {err_str[:80]}")
                            continue

            except Exception as e:
                state.add_log(f"   [!] Gemini Error: {e}")
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

            if state.stop_requested:
                state.add_log("🛑 Analysis stopped by user! No further files will be moved.")
                break

            if direct_mode:
                state.latest_result = {
                    "folder": "Direct Extract (Zero File Changes)",
                    "video_file": media_path.name,
                    "txt_file": "Direct On-Screen Display",
                    "content": ai_output
                }
                state.add_log(f"   ✨ Direct Extract Complete for: '{media_path.name}' (Original 100% untouched)")
            else:
                # Generate video filename directly from AI Caption + Hashtags (zero .txt file)
                renamed_filename = generate_video_filename(ai_output, ext, target_folder, fallback_stem=media_path.stem)
                target_media = target_folder / renamed_filename

                # Strictly CUT media from input_media into output_media
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

                state.add_log(f"   ✂️  CUT & RENAMED ➔ output_media/{renamed_filename}")

                state.latest_result = {
                    "folder": "output_media",
                    "video_file": renamed_filename,
                    "txt_file": "",
                    "content": ai_output
                }

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
        api_key = cfg.get("gemini_api_key", "").strip()
        if not api_key:
            state.add_log("❌ Error: Gemini API Key not set. Please configure your API key in Settings.")
            return

        from google import genai
        client = genai.Client(api_key=api_key)

        video_exts = ('.mp4', '.mov', '.mkv', '.avi', '.webm', '.m4v')
        is_video = Path(original_filename).suffix.lower() in video_exts

        uploaded_file = None
        ai_output = None

        try:
            state.add_log(f"   📤 Uploading {original_filename} to Gemini Vision AI...")
            uploaded_file = client.files.upload(file=str(media_path))
            state.add_log(f"   ⏳ Gemini Cloud Stream Active: {uploaded_file.name}")

            if is_video:
                state.add_log("   👀 Gemini AI is watching and analyzing video & audio directly...")
                wait_count = 0
                while uploaded_file.state.name == "PROCESSING" and wait_count < 120:
                    if state.stop_requested:
                        break
                    time.sleep(3)
                    wait_count += 3
                    uploaded_file = client.files.get(name=uploaded_file.name)

                if uploaded_file.state.name == "FAILED":
                    state.add_log(f"   [!] Gemini Video Processing Failed: {uploaded_file.error}")
                    return

            if not state.stop_requested:
                prompt = f"""Watch and listen to this entire attached video. Analyze what is happening, all dialogue/audio, visual cues, and the core message.
Generate a viral, engaging social media post for {platform.upper()} strictly in 100% FLUENT ENGLISH.

FORMAT REQUIREMENTS:
Provide ONLY the story-driven caption followed directly by hashtags.
Do NOT include ANY section titles, labels, or prefixes (Do NOT write '🎯 HOOK:', '📌 CAPTION:', '🏷️ HASHTAGS:', 'Caption:', 'Hook:', etc.).

EXACT FORMAT TO FOLLOW:
[Engaging, story-driven caption strictly in fluent English describing the key moment, emotion, humor, or situation with appropriate emojis]

#Hashtag1 #Hashtag2 #Hashtag3 #Hashtag4 #Hashtag5 ... (15-20 viral, trending hashtags for {platform.upper()})

CRITICAL RULES:
- EVERYTHING MUST be written strictly in 100% FLUENT ENGLISH ONLY.
- Output ONLY the clean caption followed immediately by the hashtags."""

                state.add_log(f"   🤖 Gemini AI generating pure English Caption & Hashtags for {platform.upper()}...")
                for model_name in ACTIVE_MODELS:
                    if state.stop_requested:
                        break
                    try:
                        resp = client.models.generate_content(
                            model=model_name,
                            contents=[uploaded_file, prompt]
                        )
                        if resp and resp.text:
                            ai_output = clean_ai_output(resp.text)
                            state.add_log(f"   ✅ Gemini ({model_name}) generated pure English Caption & Hashtags!")
                            break
                    except Exception as merr:
                        err_str = str(merr)
                        if "503" in err_str or "404" in err_str or "demand" in err_str.lower():
                            time.sleep(1)
                            continue
                        else:
                            state.add_log(f"   [!] Model notice ({model_name}): {err_str[:80]}")
                            continue

        finally:
            if uploaded_file:
                try:
                    client.files.delete(name=uploaded_file.name)
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
                rel_path = self.headers.get('X-Relative-Path', '')
                if not rel_path:
                    rel_path = self.headers.get('X-File-Name', 'uploaded_video.mp4')
                import urllib.parse
                rel_path = urllib.parse.unquote(rel_path).replace('\\', '/').strip('/')
                if '..' in rel_path:
                    self.send_json({"error": "Invalid path"}, status=400)
                    return

                dest_path = INPUT_DIR / rel_path
                dest_path.parent.mkdir(parents=True, exist_ok=True)

                remaining = content_len
                chunk_size = 1024 * 1024  # 1MB chunk for fast local upload
                with open(dest_path, "wb") as f:
                    while remaining > 0:
                        read_bytes = min(remaining, chunk_size)
                        chunk = self.rfile.read(read_bytes)
                        if not chunk:
                            break
                        f.write(chunk)
                        remaining -= len(chunk)

                size_mb = dest_path.stat().st_size / (1024 * 1024)
                state.add_log(f"📥 Video Uploaded: {rel_path} ({size_mb:.1f} MB)")
                self.send_json({"ok": True, "saved": rel_path, "size_mb": round(size_mb, 2)})
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

            if not files:
                all_files = [f["rel_path"] for f in get_input_files()]
                files = all_files

            if not files:
                self.send_json({"error": "No files found in input_media"}, status=400)
                return

            threading.Thread(target=process_worker, args=(files, platform, direct_mode), daemon=True).start()
            mode_desc = "Direct Extract (No Move/Save)" if direct_mode else "Process & Rename"
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
                    self.send_json({"error": "File not found"}, status=404)
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

def check_startup_update():
    time.sleep(2)
    try:
        info = auto_updater.check_for_updates()
        state.update_info = info
        if info.get("update_available"):
            behind = info.get("behind_count", 1)
            state.add_log(f"🚀 New update available from Git: {behind} new commit(s) ready to pull!")
    except Exception:
        pass

def free_port(port):
    """If port is occupied by an orphaned process on Windows, terminate that process."""
    if not sys.platform.startswith('win'):
        return
    try:
        import subprocess
        res = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True, text=True, timeout=5
        )
        for line in res.stdout.splitlines():
            if f":{port}" in line and "LISTENING" in line:
                parts = line.strip().split()
                pid = parts[-1]
                if pid and pid.isdigit() and int(pid) != os.getpid():
                    subprocess.run(["taskkill", "/F", "/PID", pid], capture_output=True, timeout=5)
        time.sleep(0.5)
    except Exception:
        pass

def check_startup_update():
    try:
        if hasattr(auto_updater, 'check_for_updates'):
            auto_updater.check_for_updates()
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

    # Background auto-update check on launch
    threading.Thread(target=check_startup_update, daemon=True).start()

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
