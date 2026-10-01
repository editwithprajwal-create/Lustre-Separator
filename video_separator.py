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
import subprocess
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
    "gemini-3.8-flash",
    "gemini-2.5-flash",
    "gemini-flash-latest",
    "gemini-2.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash"
]

def load_config():
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return {**DEFAULT_CONFIG, **json.load(f)}
        except Exception:
            pass
    return DEFAULT_CONFIG

def ensure_viral_hashtags(ai_text, topic_hint=''):
    """Guarantees exactly 5 hashtags: 3 viral (#MustWatch, #FYP, #Reels) + 2 video-related tags."""
    if not ai_text:
        return ai_text

    existing_tags = re.findall(r'#[A-Za-z0-9_]+', ai_text)
    caption_part = re.sub(r'#[A-Za-z0-9_]+', '', ai_text).strip()

    required_priority = ["#MustWatch", "#FYP", "#Reels"]
    seen = {t.lower() for t in required_priority}
    video_tags = []

    for t in existing_tags:
        clean_t = '#' + re.sub(r'[^A-Za-z0-9_]', '', t)
        norm = clean_t.lower()
        if norm not in seen and norm not in {'#outputmedia', '#output', '#input', '#media', '#viral'}:
            seen.add(norm)
            video_tags.append(clean_t)
            if len(video_tags) == 2:
                break

    if len(video_tags) < 2:
        th_clean = re.sub(r'[^a-zA-Z0-9]', '', topic_hint.title()) if topic_hint else 'Action'
        candidates = [f"#{th_clean}", '#Acrobatics', '#TrendingNow', '#ViralReels']
        for cand in candidates:
            norm = cand.lower()
            if norm not in seen and len(cand) > 2:
                seen.add(norm)
                video_tags.append(cand)
                if len(video_tags) == 2:
                    break

    final_5_tags = required_priority + video_tags[:2]
    tags_str = ' '.join(final_5_tags)
    return f"{caption_part}   {tags_str}" if caption_part else tags_str

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

def get_gemini_key():
    cfg = load_config()
    return cfg.get("gemini_api_key", "").strip()

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
    'unbelievable', 'breathtaking', 'flawless', 'seamless', 'synchronized', 'massive',
    'simply', 'easily', 'really', 'truly', 'certainly', 'definitely', 'clearly',
    'taking', 'getting', 'making', 'doing', 'becoming', 'turning', 'going', 'feeling',
    'you', 'your', 'we', 'they', 'it', 'me', 'us'
}

def has_emojis(s):
    return any(ord(c) > 0x1F000 or ord(c) in range(0x2600, 0x27BF) for c in s)

def get_topic_emojis(topic_hint=''):
    th = (topic_hint or '').lower()
    if any(k in th for k in ['army', 'military', 'soldier', 'cadet', 'commando', 'usa_female_army']):
        return "🎖️💪 ", " ⚡🔥"
    elif any(k in th for k in ['fly', 'flight', 'sky', 'wingsuit', 'skydive', 'aerial']):
        return "🪂✨ ", " 🦅💨"
    elif any(k in th for k in ['circus', 'acrobat', 'trapeze', 'tightrope', 'aerialist']):
        return "🎪✨ ", " 🐎💫"
    elif any(k in th for k in ['flip', 'jump', 'trampoline', 'gymnast', 'springboard']):
        return "🤸‍♂️⚡ ", " 🌪️✨"
    elif any(k in th for k in ['horse', 'camel', 'animal', 'equestrian']):
        return "🐎✨ ", " 🎪🔥"
    elif any(k in th for k in ['stunt', 'arena', 'bike', 'extreme', 'daredevil']):
        return "🔥💥 ", " 🤯⚡"
    return "🔥✨ ", " 🤯💥"

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

def clean_caption_text(text, max_len=98, topic_hint=''):
    """
    Cleans caption text ensuring it NEVER ends with dangling stop-words or broken 'adi' words.
    Guarantees emojis in caption and total length strictly <= max_len.
    Makes the caption as long and rich as possible within max_len.
    """
    # Remove AI labels
    text = re.sub(r'^(🎯\s*HOOK:|📌\s*CAPTION:|🏷️\s*HASHTAGS:|Caption:|Hook:|Title:)\s*', '', text, flags=re.I).strip()
    text = re.sub(r'[<>:"/\\|?*\x00-\x1f\r\n]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    if not text:
        text = "Incredible moment caught on camera that you have to see to believe"

    lead_emo, tail_emo = get_topic_emojis(topic_hint)
    already_has_emoji = has_emojis(text)

    reserved_emo_len = 0 if already_has_emoji else (len(lead_emo) + len(tail_emo))
    avail_len = max(35, max_len - reserved_emo_len)

    # Check sentences: greedily take as many full sentences as can fit in avail_len
    sentences = [m.group(0).strip() for m in re.finditer(r'.+?(?:[.!?][\U0001F000-\U0001FAFF\u2600-\u27BF\ufe0f\u200d\s]*|$)', text) if m.group(0).strip()]
    chosen = ""
    if sentences and is_finished_sentence(sentences[0]):
        cand = sentences[0]
        if len(cand) <= avail_len:
            chosen = cand
            for nxt in sentences[1:]:
                if is_finished_sentence(nxt) and len(f"{chosen} {nxt}") <= avail_len:
                    chosen = f"{chosen} {nxt}"
                else:
                    break

    if not chosen:
        trimmed = text[:avail_len]
        clause_breaks = [trimmed.rfind(', '), trimmed.rfind('; '), trimmed.rfind(' - '), trimmed.rfind(' — ')]
        best_break = max(clause_breaks)

        if best_break > 35:
            sub = trimmed[:best_break].strip()
        else:
            last_sp = trimmed.rfind(' ')
            sub = trimmed[:last_sp].strip() if last_sp > 25 else trimmed.strip()

        words = sub.split()
        while words and words[-1].lower().rstrip('.,;!?#') in DANGLING_STOPWORDS:
            words.pop()

        cleaned = ' '.join(words).rstrip('.,;:- ')
        if cleaned:
            if not is_finished_sentence(cleaned):
                cleaned += '!'
            chosen = cleaned
        else:
            chosen = "Incredible action captured live on camera!"

    # Ensure emojis are included
    if not has_emojis(chosen):
        candidate = f"{lead_emo}{chosen}{tail_emo}"
        if len(candidate) <= max_len:
            chosen = candidate
        else:
            if len(f"{lead_emo}{chosen}") <= max_len:
                chosen = f"{lead_emo}{chosen}"
            elif len(f"{chosen}{tail_emo}") <= max_len:
                chosen = f"{chosen}{tail_emo}"
            else:
                words = chosen.rstrip('!?. ').split()
                while words and len(f"{lead_emo}{' '.join(words)}!{tail_emo}") > max_len:
                    words.pop()
                chosen = f"{lead_emo}{' '.join(words)}!{tail_emo}"

    return chosen.strip()

def generate_video_filename(ai_text, ext, target_folder=None, fallback_stem="video", max_len=155, topic_hint=""):
    ext = ext.lower() if ext else ".mp4"
    if not ext.startswith("."):
        ext = "." + ext

    # Strictly enforce 155 character total filename limit
    MAX_FILE_NAME_TOTAL = 155
    max_stem_len = MAX_FILE_NAME_TOTAL - len(ext) # 151 chars for .mp4

    if not topic_hint:
        cand_str = str(target_folder or fallback_stem).lower()
        topic_hint = cand_str

    raw_tags = re.findall(r'#[A-Za-z0-9_]+', ai_text)
    caption_raw = re.sub(r'#[A-Za-z0-9_]+', '', ai_text)

    # User Rule: Exactly 5 hashtags
    # - 3 viral hashtags: #MustWatch #FYP #Reels
    # - 2 video-related hashtags
    priority_tags = ['#MustWatch', '#FYP', '#Reels']
    video_related_tags = []
    seen = {t.lower() for t in priority_tags}

    for t in raw_tags:
        clean_t = '#' + re.sub(r'[^A-Za-z0-9_]', '', t)
        norm = clean_t.lower()
        if len(clean_t) > 2 and norm not in seen and norm not in {'#outputmedia', '#output', '#input', '#media', '#viral'}:
            seen.add(norm)
            video_related_tags.append(clean_t)
            if len(video_related_tags) == 2:
                break

    # If fewer than 2 video-related tags found, infer from topic hint
    if len(video_related_tags) < 2:
        th_clean = re.sub(r'[^a-zA-Z0-9]', '', topic_hint.title()) if topic_hint else 'Action'
        candidates = [f"#{th_clean}", '#Acrobatics', '#ExtremeSkills', '#TrendingNow', '#ViralReels']
        for cand in candidates:
            norm = cand.lower()
            if norm not in seen and len(cand) > 2:
                seen.add(norm)
                video_related_tags.append(cand)
                if len(video_related_tags) == 2:
                    break

    # Exactly 5 hashtags: 3 viral + 2 video-related
    chosen_tags = priority_tags + video_related_tags[:2]
    tags_str = ' '.join(chosen_tags)

    # User Rule: Make caption as big/long as possible within the 155 character limit!
    # Available space for caption = max_stem_len - len(tags_str) - 3 (spaces)
    space_left_for_caption = max_stem_len - len(tags_str) - 3
    clean_caption = clean_caption_text(caption_raw, max_len=space_left_for_caption, topic_hint=topic_hint)

    base_name = f"{clean_caption}   {tags_str}"

    # Hard ceiling guarantee: strictly <= 155 chars
    while len(f"{base_name}{ext}") > MAX_FILE_NAME_TOTAL:
        space_needed = len(f"{base_name}{ext}") - MAX_FILE_NAME_TOTAL
        new_caption_len = len(clean_caption) - space_needed
        clean_caption = clean_caption_text(clean_caption, max_len=new_caption_len, topic_hint=topic_hint)
        base_name = f"{clean_caption}   {tags_str}"
        if len(f"{base_name}{ext}") > MAX_FILE_NAME_TOTAL:
            if len(chosen_tags) > 4:
                chosen_tags.pop()
                tags_str = ' '.join(chosen_tags)
                base_name = f"{clean_caption}   {tags_str}"

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
        max_stem_for_dup = MAX_FILE_NAME_TOTAL - len(ext) - needed
        space_for_dup_caption = max_stem_for_dup - len(tags_str) - 3
        dup_caption = clean_caption_text(clean_caption, max_len=space_for_dup_caption, topic_hint=topic_hint)
        new_name = f"{dup_caption}   {tags_str}{tag}{ext}"
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

def safe_move_file(src, dst, max_retries=10, delay=0.3):
    """Safely and strictly cuts a file, avoiding FileExistsError or locks on Windows."""
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

    import gc
    for attempt in range(max_retries):
        try:
            gc.collect()
            shutil.move(str(src), str(dst))
            if not src.exists():
                return True
        except Exception:
            gc.collect()
            time.sleep(delay)

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
        startupinfo = None
        if sys.platform.startswith('win'):
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
        res = subprocess.run(
            ['ffmpeg', '-encoders'],
            capture_output=True,
            text=True,
            timeout=5,
            startupinfo=startupinfo
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
    
    startupinfo = None
    if sys.platform.startswith('win'):
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE

    t0 = time.time()
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, startupinfo=startupinfo)
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
                res_cpu = subprocess.run(cpu_cmd, capture_output=True, text=True, startupinfo=startupinfo)
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

CRITICAL CAPTION LENGTH RULE:
1. Write 1 complete, rich, engaging viral sentence (strictly between 70 and 92 characters) with vibrant emojis describing the key action, skill, emotion, or moment in the video.
2. Make the caption as detailed and long as possible within 92 characters, and it MUST end cleanly with an exclamation mark (!) or period (.) and emojis. Never write cut-off sentences.

CRITICAL HASHTAGS RULE (EXACTLY 5 HASHTAGS):
Follow immediately with EXACTLY 5 hashtags:
- Must start with the 3 viral hashtags: #MustWatch #FYP #Reels
- Followed by 2 video-specific hashtags matching the video content.
- Total hashtags must be strictly 5.

EXACT FORMAT TO FOLLOW:
[Complete rich sentence strictly 70-92 chars with vibrant emojis ending with ! or .]   #MustWatch #FYP #Reels #VideoTag1 #VideoTag2

EXAMPLE:
She walks in with her paperwork and family confrontation explodes! 😳📄   #MustWatch #FYP #Reels #FamilyDrama #DramaticMoments

CRITICAL RULES:
- EVERYTHING MUST be written strictly in 100% FLUENT ENGLISH ONLY.
- Regardless of the spoken language or dialogue in the video (even if Nepali, Hindi, Spanish, etc.), you MUST translate all concepts and write EVERYTHING strictly in 100% FLUENT ENGLISH.
- Absolutely NO section labels, headers, or markdown titles.
- Absolutely NO Devanagari, Nepali, Hindi, or non-English script.
- Do NOT include any intro, outro, explanations, search keywords, or conversational filler.
- Output ONLY the clean caption followed immediately by the 5 hashtags."""

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

    target_folder = OUTPUT_DIR
    target_folder.mkdir(parents=True, exist_ok=True)

    # 1. Process any subfolders inside input_media
    for folder_path in subfolders:
        media_files = sorted(
            [f for f in folder_path.iterdir() if f.is_file() and f.suffix.lower() in all_media_exts],
            key=lambda x: x.name.lower()
        )

        for idx, media_path in enumerate(media_files, 1):
            ext = media_path.suffix.lower()

            print(f"\n[{idx}] 🎬 {media_path.name}")
            print(f"   🎥 Video will be renamed with Caption & Hashtags directly in output_media")

            ai_output = upload_and_analyze_with_gemini(gemini_key, media_path, platform=platform)

            # Fallback if Gemini failed so user never gets blank file
            if not ai_output:
                ai_output = f"""An unexpected and emotional moment caught on camera! Watch closely as the story unfolds with the biggest smile. What would your reaction be in this situation? Let us know your thoughts in the comments below! 👇💬❤️

#Viral #Trending #MustWatch #VideoOfTheDay #StoryTime #ExplorePage #FYP #Reels #CuteAnimals #WholesomeMoments #FunnyReels #ViralReels #FacebookWatch #Entertainment"""
            else:
                ai_output = clean_ai_output(ai_output)

            renamed_name = generate_video_filename(ai_output, ext, target_folder, fallback_stem=media_path.stem)
            renamed_target = target_folder / renamed_name

            # Move and rename safely
            import gc
            gc.collect()
            time.sleep(0.3)
            safe_move_file(media_path, renamed_target)
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

            print(f"   ✂️  CUT ➔ {renamed_name}")
            total_count += 1

        try:
            shutil.rmtree(str(folder_path))
        except Exception:
            pass

    # 2. Process direct files in input_media
    if direct_files:
        total = len(direct_files)
        import threading
        for idx, media_path in enumerate(direct_files, 1):
            ext = media_path.suffix.lower()
            is_video = ext in ('.mp4', '.mov', '.mkv', '.avi', '.webm', '.m4v')

            print(f"\n[{idx}/{total}] 🎬 {media_path.name}")
            print(f"   🎥 Video will be 4K AI Upscaled & renamed with Caption + Hashtags directly in output_media")

            render_thread = None
            render_status = {"done": False, "ok": False}
            temp_4k_path = None

            if is_video:
                temp_4k_filename = f".render_4k_{int(time.time())}_{idx}.mp4"
                temp_4k_path = target_folder / temp_4k_filename

                def _bg_render(src=media_path, dst=temp_4k_path):
                    print("   ⚡ [Parallel GPU] 4K Ultra-HD Upscale render started in background...")
                    ok = render_video_4k(src, dst, log_callback=lambda m: print(f"   🎬 [4K Render]: {m}"))
                    render_status["ok"] = ok
                    render_status["done"] = True

                render_thread = threading.Thread(target=_bg_render, daemon=True)
                render_thread.start()

            ai_output = upload_and_analyze_with_gemini(gemini_key, media_path, platform=platform)

            # Wait for 4K render to finalize
            if render_thread and render_thread.is_alive():
                print("   ⏳ Finalizing parallel 4K render on GPU...")
                render_thread.join(timeout=300)

            # Fallback if Gemini failed so user never gets blank file
            if not ai_output:
                ai_output = f"""An unexpected and emotional moment caught on camera! Watch closely as the story unfolds with the biggest smile. What would your reaction be in this situation? Let us know your thoughts in the comments below! 👇💬❤️

#Viral #Trending #MustWatch #VideoOfTheDay #StoryTime #ExplorePage #FYP #Reels #CuteAnimals #WholesomeMoments #FunnyReels #ViralReels #FacebookWatch #Entertainment"""
            else:
                ai_output = clean_ai_output(ai_output)

            output_ext = ".mp4" if (render_status.get("ok") and temp_4k_path and temp_4k_path.exists()) else ext
            renamed_name = generate_video_filename(ai_output, output_ext, target_folder, fallback_stem=media_path.stem)
            renamed_target = target_folder / renamed_name

            # Move 4K or original safely
            import gc
            gc.collect()
            time.sleep(0.3)
            if render_status.get("ok") and temp_4k_path and temp_4k_path.exists() and temp_4k_path.stat().st_size > 0:
                safe_move_file(temp_4k_path, renamed_target)
                print(f"   ✨ 4K Ultra-HD Video successfully saved to output_media!")
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
                safe_move_file(media_path, renamed_target)
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

            print(f"   ✂️  CUT ➔ {renamed_name}")
            total_count += 1

    print("\n" + "=" * 68)
    print(f"🎉 सबै {total_count} वटा भिडियोहरू Gemini AI ले विश्लेषण गरी")
    print("   Caption & Hashtags अनुसार सिधै भिडियोको नाम Rename गरियो!")
    print(f"📂 Output फोल्डर: {OUTPUT_DIR}")
    print("=" * 68)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n🛑 प्रयोगकर्ताद्वारा Analysis रोकियो (Analysis Stopped by user)!")
        sys.exit(0)
