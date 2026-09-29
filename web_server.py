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

# UTF-8 stdout on Windows
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# Base Directories
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

def process_worker(file_rel_paths, platform):
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

            if media_path.parent != INPUT_DIR:
                folder_name = media_path.parent.name
            else:
                folder_name = media_path.stem

            ext = media_path.suffix.lower()
            target_folder = OUTPUT_DIR / folder_name
            target_folder.mkdir(parents=True, exist_ok=True)
            video_index = get_next_available_index(target_folder)
            renamed_filename = f"{video_index}{ext}"

            state.add_log(f"🎬 [{idx}/{len(file_rel_paths)}] Processing: {media_path.name}")
            state.add_log(f"   📁 Folder Name (Unchanged): {folder_name}/")
            state.add_log(f"   🎥 Renaming Video to: {renamed_filename}")

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

            if state.stop_requested:
                state.add_log("🛑 Analysis stopped by user! No further files will be moved.")
                break

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

            state.add_log(f"   ✂️  CUT & RENAMED ➔ {target_folder.name}/{renamed_filename}")
            state.add_log(f"   📝 Pure English .txt Saved: {txt_path.name}")

            state.latest_result = {
                "folder": target_folder.name,
                "video_file": renamed_filename,
                "txt_file": txt_path.name,
                "content": ai_output
            }

        if not state.stop_requested:
            state.add_log(f"🎉 Success! Finished processing {len(file_rel_paths)} video(s).")
    except Exception as exc:
        state.add_log(f"❌ Unexpected processing error: {exc}")
    finally:
        state.is_processing = False
        state.stop_requested = False

class LustreHTTPHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WORKSPACE_DIR), **kwargs)

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
        else:
            if path == "/" or path == "":
                self.path = "/index.html"
            super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        content_len = int(self.headers.get('Content-Length', 0))

        if path == "/api/upload":
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
            chunk_size = 64 * 1024
            with open(dest_path, "wb") as f:
                while remaining > 0:
                    read_bytes = min(remaining, chunk_size)
                    chunk = self.rfile.read(read_bytes)
                    if not chunk:
                        break
                    f.write(chunk)
                    remaining -= len(chunk)

            size_mb = dest_path.stat().st_size / (1024 * 1024)
            state.add_log(f"📥 Drag & Drop: Saved {rel_path} ({size_mb:.1f} MB)")
            self.send_json({"ok": True, "saved": rel_path})
            return

        body = self.rfile.read(content_len).decode('utf-8') if content_len > 0 else "{}"
        try:
            data = json.loads(body)
        except Exception:
            data = {}

        if path == "/api/process":
            if state.is_processing:
                self.send_json({"error": "Already processing"}, status=400)
                return
            
            files = data.get("files", [])
            platform = data.get("platform", "facebook")

            if not files:
                all_files = [f["rel_path"] for f in get_input_files()]
                files = all_files

            if not files:
                self.send_json({"error": "No files found in input_media"}, status=400)
                return

            threading.Thread(target=process_worker, args=(files, platform), daemon=True).start()
            self.send_json({"message": f"Processing started for {len(files)} file(s)"})

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
            try:
                os.startfile(str(OUTPUT_DIR))
                self.send_json({"message": "Output folder opened"})
            except Exception as e:
                self.send_json({"error": str(e)}, status=500)

        elif path == "/api/open_input":
            try:
                os.startfile(str(INPUT_DIR))
                self.send_json({"message": "Input folder opened"})
            except Exception as e:
                self.send_json({"error": str(e)}, status=500)

        elif path == "/api/clear_result":
            with state.lock:
                state.latest_result = None
            self.send_json({"ok": True, "message": "Result cleared"})

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

def run_server(port=5050, open_browser=True):
    server = ThreadingHTTPServer(("127.0.0.1", port), LustreHTTPHandler)
    url = f"http://localhost:{port}"
    print("=" * 64)
    print(f"✨ Lustre Separator Web Server is running at: {url}")
    print("=" * 64)

    # Background auto-update check on launch
    threading.Thread(target=check_startup_update, daemon=True).start()

    if open_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Web Server...")
        server.shutdown()

if __name__ == "__main__":
    port = 5050
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except Exception:
            pass
    run_server(port=port, open_browser=True)
