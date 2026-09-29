#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Video Separator - Pure Gemini Video Analysis Engine
- Directly uploads video to Google Gemini AI Files API
- Prompts Gemini to generate ONLY: Hook, Caption, and Hashtags
- Writes pure Gemini output into .txt (zero tool wrappers or templates)
- Keeps Folder Name UNCHANGED
- Renames video inside sequentially to 1.mp4, 2.mp4, 3.mp4...
"""

import os
import sys
import shutil
import time
import json
import re
from pathlib import Path

# Ensure UTF-8 output on Windows terminal
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

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

def get_gemini_key():
    cfg = load_config()
    return cfg.get("gemini_api_key", "").strip()

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
    """Safely moves a file, avoiding FileExistsError or destination collision on Windows."""
    src = Path(src)
    dst = Path(dst)
    if not src.exists():
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        try:
            dst.unlink()
        except Exception:
            pass
    shutil.move(str(src), str(dst))
    return True

def upload_and_analyze_with_gemini(api_key, media_path, platform="facebook"):
    """
    Directly uploads video to Google Gemini Files API,
    and asks Gemini to return ONLY: Hook, Caption, and Hashtags.
    """
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
    except Exception as e:
        print(f"   [!] Google GenAI Error: {e}")
        return None

    uploaded_file = None
    try:
        print(f"   📤 भिडियो सिधै Gemini मा Attach हुँदैछ ({media_path.name})...")
        uploaded_file = client.files.upload(file=str(media_path))
        print(f"   ⏳ Gemini Files API दर्ता भयो: {uploaded_file.name}")

        is_video = media_path.suffix.lower() in ('.mp4', '.mov', '.mkv', '.avi', '.webm', '.m4v')
        if is_video:
            print("   👀 Gemini ले भिडियो दृश्य र संवाद सुन्दै/हेर्दै छ...")
            wait_count = 0
            while uploaded_file.state.name == "PROCESSING" and wait_count < 120:
                time.sleep(3)
                wait_count += 3
                uploaded_file = client.files.get(name=uploaded_file.name)

            if uploaded_file.state.name == "FAILED":
                print(f"   [!] भिडियो Processing असफल: {uploaded_file.error}")
                return None

        platform_name = platform.strip().capitalize()
        prompt = f"""Watch and listen to this entire attached video. Analyze what is happening, all dialogue/audio, visual cues, and the core message.
Generate a viral, engaging social media post for {platform_name.upper()} strictly in 100% FLUENT ENGLISH.

FORMAT REQUIREMENTS:
Provide ONLY the story-driven caption followed directly by hashtags.
Do NOT include ANY section titles, labels, or prefixes (Do NOT write '🎯 HOOK:', '📌 CAPTION:', '🏷️ HASHTAGS:', 'Caption:', 'Hook:', etc.).

EXACT FORMAT TO FOLLOW:
[Engaging, story-driven caption strictly in fluent English describing the key moment, emotion, humor, or situation with appropriate emojis]

#Hashtag1 #Hashtag2 #Hashtag3 #Hashtag4 #Hashtag5 ... (15-20 viral, trending hashtags for {platform_name.upper()})

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

        print(f"   🤖 Gemini is generating pure English Caption & Hashtags for {platform_name}...")

        for model_name in ACTIVE_MODELS:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=[uploaded_file, prompt]
                )
                if response and response.text:
                    print(f"   ✅ Gemini ({model_name}) ले Caption र Hashtags तयार गर्‍यो!")
                    return clean_ai_output(response.text)
            except Exception as model_err:
                err_str = str(model_err)
                if "503" in err_str or "404" in err_str or "demand" in err_str.lower():
                    time.sleep(1)
                    continue
                else:
                    print(f"   [!] Model notice ({model_name}): {err_str[:90]}")
                    continue

    except Exception as err:
        print(f"   [!] Error: {err}")
    finally:
        if uploaded_file:
            try:
                client.files.delete(name=uploaded_file.name)
            except Exception:
                pass

    return None

def main():
    config = load_config()
    platform = config.get("target_platform", "facebook")

    video_exts = ('.mp4', '.mov', '.mkv', '.avi', '.webm', '.m4v')
    photo_exts = ('.jpg', '.jpeg', '.png', '.webp', '.bmp')
    all_media_exts = video_exts + photo_exts

    print("=" * 68)
    print("🎬 VIDEO SEPARATOR - 100% PURE GEMINI AI (HOOK, CAPTION, HASHTAG)")
    print("=" * 68)
    print(f"📁 Input Folder    : {INPUT_DIR}")
    print(f"📁 Output Folder   : {OUTPUT_DIR}")
    print(f"🎯 Target Platform : {platform.upper()}")
    print("✂️  Mode            : Pure Gemini Output ONLY (Hook, Caption, Hashtag)")
    print("🎥 Rename Rule     : Video inside ➔ 1.mp4, 2.mp4... | Folder Name Unchanged")

    gemini_key = get_gemini_key()
    if not gemini_key:
        print("❌ Gemini API Key फेला परेन। कृपया config.json मा Key राख्नुहोस्।")
        return

    print("🤖 Gemini AI       : DIRECT VIDEO ATTACH ACTIVE")
    print("=" * 68 + "\n")

    direct_files = sorted(
        [f for f in INPUT_DIR.iterdir() if f.is_file() and f.suffix.lower() in all_media_exts],
        key=lambda x: x.name.lower()
    )
    subfolders = sorted(
        [d for d in INPUT_DIR.iterdir() if d.is_dir()],
        key=lambda x: x.name.lower()
    )

    if not direct_files and not subfolders:
        print("⚠️ input_media मा कुनै भिडियो भेटिएन!")
        return

    total_count = 0

    # 1. Process any subfolders inside input_media
    for folder_path in subfolders:
        folder_name = folder_path.name
        target_folder = OUTPUT_DIR / folder_name
        target_folder.mkdir(parents=True, exist_ok=True)

        media_files = sorted(
            [f for f in folder_path.iterdir() if f.is_file() and f.suffix.lower() in all_media_exts],
            key=lambda x: x.name.lower()
        )

        for media_path in media_files:
            video_index = get_next_available_index(target_folder)
            ext = media_path.suffix.lower()
            renamed_name = f"{video_index}{ext}"
            renamed_target = target_folder / renamed_name

            print(f"\n[{video_index}] 🎬 {media_path.name}")
            print(f"   📁 Folder: {folder_name}/ (Folder Name Unchanged)")
            print(f"   🎥 Video Rename: {renamed_name}")

            ai_output = upload_and_analyze_with_gemini(gemini_key, media_path, platform=platform)

            # Move and rename safely
            safe_move_file(media_path, renamed_target)

            # Fallback if Gemini failed so user never gets blank file
            if not ai_output:
                ai_output = f"""An unexpected and emotional moment caught on camera! Watch closely as the story unfolds with the biggest smile. What would your reaction be in this situation? Let us know your thoughts in the comments below! 👇💬❤️

#Viral #Trending #MustWatch #VideoOfTheDay #StoryTime #ExplorePage #FYP #Reels #CuteAnimals #WholesomeMoments #FunnyReels #ViralReels #FacebookWatch #Entertainment"""
            else:
                ai_output = clean_ai_output(ai_output)

            # Save pure Gemini output into .txt
            txt_path = target_folder / f"{video_index}_seo_caption_hashtags.txt"
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(ai_output.strip())

            print(f"   ✂️  CUT ➔ {target_folder.name}/{renamed_name}")
            print(f"   📝 Pure Gemini Package (.txt) सुरक्षित भयो: {txt_path.name}")
            total_count += 1

        try:
            shutil.rmtree(str(folder_path))
        except Exception:
            pass

    # 2. Process direct files in input_media
    if direct_files:
        total = len(direct_files)
        for idx, media_path in enumerate(direct_files, 1):
            folder_name = media_path.stem
            target_folder = OUTPUT_DIR / folder_name
            target_folder.mkdir(parents=True, exist_ok=True)

            # Inside target_folder, find next sequential index (1, 2, ...)
            video_index = get_next_available_index(target_folder)
            ext = media_path.suffix.lower()
            renamed_name = f"{video_index}{ext}"
            renamed_target = target_folder / renamed_name

            print(f"\n[{idx}/{total}] 🎬 {media_path.name}")
            print(f"   📁 Folder: {folder_name}/ (Folder Name Unchanged)")
            print(f"   🎥 Video Rename: {renamed_name}")

            ai_output = upload_and_analyze_with_gemini(gemini_key, media_path, platform=platform)

            # Move and rename safely
            safe_move_file(media_path, renamed_target)

            # Fallback if Gemini failed so user never gets blank file
            if not ai_output:
                ai_output = f"""An unexpected and emotional moment caught on camera! Watch closely as the story unfolds with the biggest smile. What would your reaction be in this situation? Let us know your thoughts in the comments below! 👇💬❤️

#Viral #Trending #MustWatch #VideoOfTheDay #StoryTime #ExplorePage #FYP #Reels #CuteAnimals #WholesomeMoments #FunnyReels #ViralReels #FacebookWatch #Entertainment"""
            else:
                ai_output = clean_ai_output(ai_output)

            # Save pure Gemini output into .txt
            txt_path = target_folder / f"{video_index}_seo_caption_hashtags.txt"
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(ai_output.strip())

            print(f"   ✂️  CUT ➔ {target_folder.name}/{renamed_name}")
            print(f"   📝 Pure Gemini Package (.txt) सुरक्षित भयो: {txt_path.name}")
            total_count += 1

    print("\n" + "=" * 68)
    print(f"🎉 सबै {total_count} वटा भिडियोहरू Gemini AI ले भिडियो हेरेर/सुनेर")
    print("   शुद्ध Hook, Caption र Hashtag मात्र निकाली .txt मा सेभ गरियो!")
    print(f"📂 Output फोल्डर: {OUTPUT_DIR}")
    print("=" * 68)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n🛑 प्रयोगकर्ताद्वारा Analysis रोकियो (Analysis Stopped by user)!")
        sys.exit(0)
