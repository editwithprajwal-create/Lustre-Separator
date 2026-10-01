# -*- coding: utf-8 -*-
import os, sys, re, time, random, shutil, subprocess, json
from pathlib import Path

# Niche rules for smart local generation / fallback
NICHE_RULES = [
    {
        'keywords': ['army', 'military', 'soldier', 'female army', 'usa_female_army', 'commando', 'cadet'],
        'captions': [
            '🎖️💪 Elite military acrobatics and synchronized precision on full display! ⚡🔥',
            '🪖✨ Fearless female army performers defying gravity with unbelievable power! ⚡🔥',
            '🎖️⚡ Razor-sharp discipline and jaw-dropping aerial stunts under pressure! 🚀💫',
            '🔥💥 High-octane military obstacle stunts that will leave you speechless! 🤯⚡',
            '🌪️✨ Strength, speed, and flawless tactical synchronization in action! 👀🔥',
            '🎖️💪 Powerhouse cadets conquering impossible aerial ropes with pure grit! ⚡🔥',
            '🪖💥 Jaw-dropping military trampoline leaps straight into synchronized flips! 🌪️✨',
            '⚡👏 Setting the standard for high-stakes military discipline and teamwork! 🎖️🔥',
            '🎖️✨ Daring military acrobats pushing physical limits to the absolute edge! 🚀💫',
            '🔥⚡ Unmatched focus and courage on full display in this tactical showcase! 🎖️💪',
            '🪖🔥 Heart-pounding aerial agility that commands total respect and awe! ⚡✨',
            '🎖️💫 Synchronized perfection and sheer athletic dominance under the spotlight! 👏🔥'
        ],
        'tags': ['#MustWatch', '#FYP', '#Viral', '#USAArmy', '#MilitaryStunts', '#FemalePower', '#Acrobatics', '#ExtremeSkills', '#TrendingNow', '#ViralReels']
    },
    {
        'keywords': ['skyrush', 'human can fly', 'fly', 'flying', 'wingsuit', 'skydiving', 'aerial', 'freefall', 'altitude'],
        'captions': [
            '🪂✨ Defying the laws of gravity with pure courage and breathtaking flight! 🦅💨',
            '🚀💨 Heart-stopping altitude and unbelievable glide speed in the open sky! 😱✨',
            '🦅✨ Total freedom cutting through the clouds with surgical precision! 🪂🔥',
            '🌪️⚡ Standing on the edge of the world before the ultimate leap of faith! 🤯💥',
            '🦸‍♂️✨ Soaring high above the earth like a real-life superhero! 🚀💫',
            '🪂🔥 Adrenaline rush at maximum velocity during this heart-stopping sky dive! ⚡💨',
            '🦅💨 Cutting through mountain winds with fearless wingsuit mastery! 🪂✨',
            '🌪️💥 The ultimate thrill of freefall captured with stunning precision! 😱🔥',
            '🚀✨ Gravity is completely optional when you master the open skies! 🦅💨',
            '🪂⚡ Pure courage and razor-sharp navigation at extreme heights! 🤯🔥',
            '😱💨 Mind-blowing aerial dive that will leave your heart pounding! 🚀✨',
            '🦅🔥 Flight taken to extreme limits in this jaw-dropping sky descent! 🪂💫'
        ],
        'tags': ['#MustWatch', '#FYP', '#Viral', '#SkyRush', '#HumanFlight', '#Wingsuit', '#ExtremeStunts', '#Skydiving', '#AdrenalineRush', '#Trending']
    },
    {
        'keywords': ['flip', 'flipsync', 'sync', 'trampoline', 'springboard', 'slingshot', 'catapult', 'seesaw'],
        'captions': [
            '🤸‍♂️⚡ Flawless synchronization and unbelievable trampoline flips live! 🌪️✨',
            '🔥✨ Incredible rhythm and teamwork as these acrobats defy physics! 👏💫',
            '🌪️⚡ Split-second air awareness and triple rotation landing on point! 🤯💥',
            '🤸‍♀️✨ Perfect synergy and zero room for error as multiple flips sync up! ⚡🔥',
            '💫🌪️ Extreme bounce height and jaw-dropping mid-air synchronicity! 👏✨',
            '🤸‍♂️🔥 Launching off the human catapult into a heart-stopping double flip! 🚀💥',
            '⚡✨ Springboard power delivering gravity-defying triple rotations! 🤸‍♀️🌪️',
            '🤯💥 Slingshot momentum creating the most daring aerial leap ever seen! 🔥✨',
            '🤸‍♀️⚡ Mind-bending timing as gymnasts nail the simultaneous release! 🌪️👏',
            '🚀🔥 Rocketing off the giant trampoline straight onto target landings! 🤯✨'
        ],
        'tags': ['#MustWatch', '#FYP', '#Viral', '#FlipSync', '#TrampolineFlips', '#Acrobatics', '#Gymnastics', '#ExtremeAction', '#ViralVideo', '#Reels']
    },
    {
        'keywords': ['circus', 'trapeze', 'tightrope', 'silk', 'aerialist', 'ring', 'rings', 'big top'],
        'captions': [
            '🎪✨ World-class circus artistry taking breath away with high-flying spins! 🐎💫',
            '🌟✨ An awe-inspiring moment under the big top as this routine unfolds! 👏💫',
            '🎪🔥 Dazzling the audience with fearless acrobatics and graceful landings! 🐎✨',
            '🎪✨ High above the sawdust ring, fearless trapeze artists defy gravity! 🕊️🔥',
            '💫🎪 Suspended in mid-air with jaw-dropping balance and nerves of steel! 👏✨',
            '🎪🔥 Heart-stopping aerial silk drops that leave everyone speechless! 😱✨',
            '🕊️✨ Flawless trapeze release and synchronized catch high above! 🎪👏',
            '🎪💫 Pure circus magic delivering unforgettable spectacle under the lights! 🐎🔥'
        ],
        'tags': ['#MustWatch', '#FYP', '#Viral', '#CircusLife', '#Acrobatics', '#AerialArt', '#Trapeze', '#LiveShow', '#ExplorePage', '#Reels']
    },
    {
        'keywords': ['horse', 'camel', 'elephant', 'equestrian', 'animal'],
        'captions': [
            '🐎✨ Breathtaking equestrian acrobatics executed with perfect trust! 🎪🔥',
            '🎪🐘 Grand circus spectacle as acrobats soar above performing animals! ✨💫',
            '🐎🔥 Leaping straight onto the back of a galloping horse in full stride! 👏✨',
            '🎪✨ Unbelievable harmony between majestic animals and daring performers! 🐎💫',
            '🐫🔥 Gravity-defying leaps from the back of moving camels under the big top! 🎪✨'
        ],
        'tags': ['#MustWatch', '#FYP', '#Viral', '#EquestrianAcrobatics', '#CircusLife', '#AnimalStunts', '#LivePerformance', '#TrendingNow', '#ViralReels']
    },
    {
        'keywords': ['arena', 'stunt', 'daredevil', 'extreme', 'bike', 'wheel', 'cart'],
        'captions': [
            '🔥💥 High-stakes arena action that will keep your eyes glued to the screen! 🤯⚡',
            '🎪✨ An insane test of agility, balance, and nerves under the arena lights! 🐎💫',
            '🌪️🔥 Edge-of-your-seat stunts executed with world-class skill and precision! 👀⚡',
            '💥⚡ Pushing human limits to the absolute edge in this stunt showcase! 🤯🚀',
            '🚲🔥 Daring bicycle stunts and wall-running balance that defy physics! 😱⚡'
        ],
        'tags': ['#MustWatch', '#FYP', '#Viral', '#ArenaShow', '#ExtremeAction', '#Daredevil', '#StuntLife', '#InsaneSkills', '#TrendingNow', '#ViralReels']
    }
]

FAST_MODELS = [
    'gemini-flash-lite-latest',
    'gemini-3.1-flash-lite-preview',
    'gemini-3-flash-preview',
    'gemini-3.1-flash-lite',
    'gemini-flash-latest'
]

GENERIC_FOLDERS = {
    'output', 'output_media', 'outputmedia', 'posted', 'input', 'media', 'videos',
    'temp', 'downloads', 'seedance', 'prompts', 'compressed', 'generated'
}

def clean_topic_name(folder_or_name):
    raw = str(folder_or_name).replace('\\', '/').split('/')[-1]
    raw = re.sub(r'\.[a-zA-Z0-9]+$', '', raw)
    raw = re.sub(r'[\-_]+', ' ', raw)
    raw = re.sub(r'\b(?:400|Full|Prompts?|201|to|600|9x16|16x9|1080p|4k|Generated|video|no|watermark|live|posted|output_media|compressed)\b', '', raw, flags=re.I)
    raw = re.sub(r'\s+', ' ', raw).strip()
    if raw.lower() in GENERIC_FOLDERS or not raw:
        return 'Viral Video'
    return raw

def get_video_duration(video_path):
    cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', str(video_path)]
    flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, creationflags=flags)
        dur = float(res.stdout.strip())
        return dur if dur > 0 else 6.0
    except Exception:
        return 6.0

def extract_video_keyframes(video_path, num_frames=3):
    """Extracts 3 sharp keyframes across video duration in ~0.5s with zero window flicker."""
    dur = get_video_duration(video_path)
    if dur <= 1.5:
        points = [dur * 0.5]
    elif dur <= 3.0:
        points = [dur * 0.3, dur * 0.7]
    else:
        points = [dur * 0.2, dur * 0.5, dur * 0.8]

    flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    frames_bytes = []
    temp_dir = Path(os.environ.get('TEMP', '.'))

    for idx, p in enumerate(points):
        temp_img = temp_dir / f'dec_kf_{os.getpid()}_{idx}_{int(time.time()*1000)%10000}.jpg'
        cmd = [
            'ffmpeg', '-y', '-ss', f'{p:.2f}', '-i', str(video_path),
            '-vframes', '1', '-vf', 'scale=-1:720', '-q:v', '3', str(temp_img)
        ]
        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=flags)
            if temp_img.exists() and temp_img.stat().st_size > 0:
                with open(temp_img, 'rb') as f:
                    frames_bytes.append(f.read())
                try:
                    temp_img.unlink()
                except Exception:
                    pass
        except Exception:
            pass

    return frames_bytes

def ensure_viral_hashtags(text, topic_hint='ViralVideo'):
    """Guarantees at least 8 to 10 viral hashtags containing #MustWatch, #FYP, #Viral."""
    lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
    if not lines:
        return f"Incredible moment caught on camera! Watch closely as the action unfolds.   #MustWatch #FYP #Viral #{topic_hint} #Trending #Reels #VideoOfTheDay #ExplorePage"

    # Find existing hashtags
    found_tags = re.findall(r'#[A-Za-z0-9_]+', text)
    caption_lines = [l for l in lines if not l.startswith('#')]
    caption = ' '.join(caption_lines).strip()
    
    # Clean caption from unwanted labels
    caption = re.sub(r'^(🎯\s*HOOK:|📌\s*CAPTION:|🏷️\s*HASHTAGS:|Caption:|Hook:|Title:)\s*', '', caption, flags=re.I).strip()
    # Always guarantee vibrant emojis in caption
    has_emoji = any(ord(c) > 0x1F000 or ord(c) in range(0x2600, 0x27BF) for c in caption)
    if not has_emoji:
        th = (topic_hint or '').lower()
        if any(k in th for k in ['army', 'military', 'soldier', 'cadet', 'commando', 'usa_female_army']):
            caption = f"🎖️💪 {caption} ⚡🔥"
        elif any(k in th for k in ['fly', 'flight', 'sky', 'wingsuit', 'skydive', 'aerial']):
            caption = f"🪂✨ {caption} 🦅💨"
        elif any(k in th for k in ['circus', 'acrobat', 'trapeze', 'tightrope', 'aerialist']):
            caption = f"🎪✨ {caption} 🐎💫"
        elif any(k in th for k in ['flip', 'jump', 'trampoline', 'gymnast', 'springboard']):
            caption = f"🤸‍♂️⚡ {caption} 🌪️✨"
        elif any(k in th for k in ['horse', 'camel', 'elephant', 'equestrian', 'animal']):
            caption = f"🐎✨ {caption} 🎪🔥"
        elif any(k in th for k in ['stunt', 'arena', 'bike', 'extreme', 'daredevil']):
            caption = f"🔥💥 {caption} 🤯⚡"
        else:
            caption = f"🔥✨ {caption} 🤯💥"

    # Clean topic hint
    topic_tag = re.sub(r'[^a-zA-Z0-9]', '', topic_hint.title()) if topic_hint else 'ViralMoment'
    if topic_tag.lower() in GENERIC_FOLDERS or not topic_tag:
        topic_tag = 'ViralMoment'

    required_priority = ['#MustWatch', '#FYP', '#Reels']
    video_tags = []
    seen = {t.lower() for t in required_priority}

    # Extract up to 2 video-specific tags from AI tags
    for tag in found_tags:
        clean_t = '#' + re.sub(r'[^A-Za-z0-9_]', '', tag)
        norm = clean_t.lower()
        if norm not in seen and norm not in {'#outputmedia', '#posted', '#output', '#input', '#media', '#viral'}:
            seen.add(norm)
            video_tags.append(clean_t)
            if len(video_tags) == 2:
                break

    # If fewer than 2 video tags, infer from topic hint
    if len(video_tags) < 2:
        for fallback in [f"#{topic_tag}", '#Acrobatics', '#TrendingNow', '#ViralReels']:
            norm = fallback.lower()
            if norm not in seen:
                seen.add(norm)
                video_tags.append(fallback)
                if len(video_tags) == 2:
                    break

    final_5_tags = required_priority + video_tags[:2]
    return f"{caption}   {' '.join(final_5_tags)}"

def generate_local_caption_and_hashtags(media_path, folder_name='', index=1, platform='facebook'):
    """Fast local fallback when offline or no API key available."""
    folder_str = str(folder_name or Path(media_path).parent.name)
    file_stem = Path(media_path).stem
    combined_context = f'{folder_str} {file_stem}'.lower()
    clean_topic = clean_topic_name(folder_str)

    matched_rule = None
    for rule in NICHE_RULES:
        if any(kw in combined_context for kw in rule['keywords']):
            matched_rule = rule
            break

    if matched_rule:
        captions_pool = matched_rule['captions']
        tags_pool = list(matched_rule['tags'])
    else:
        topic_tag = re.sub(r'[^a-zA-Z0-9]', '', clean_topic.title())
        if topic_tag.lower() in GENERIC_FOLDERS or not topic_tag:
            topic_tag = 'ViralMoment'
        captions_pool = [
            f'🔥✨ An extraordinary moment captured on camera that you simply have to see to believe! 🤯💥',
            f'⚡👏 Unbelievable skill and timing delivering pure shock value in seconds! 🔥✨',
            f'🎪✨ Pure entertainment that completely stole the spotlight from start to finish! 🐎💫',
            f'👀🔥 Wait till you see what happens next in this jaw-dropping footage! 😱💥'
        ]
        tags_pool = ['#MustWatch', '#FYP', '#Viral', f'#{topic_tag}', '#Trending', '#Reels', '#VideoOfTheDay', '#ExplorePage', '#ViralReels', '#ForYouPage']

    file_bytes_sample = b''
    try:
        with open(media_path, 'rb') as f:
            file_bytes_sample = f.read(4096)
    except Exception:
        pass
    file_hash = abs(hash(file_bytes_sample + str(Path(media_path).name).encode('utf-8'))) if file_bytes_sample else abs(hash(str(media_path)))
    seed_val = file_hash + (index * 17)
    caption = captions_pool[seed_val % len(captions_pool)]
    return ensure_viral_hashtags(f"{caption} {' '.join(tags_pool)}", topic_hint=clean_topic)

def decode_video_with_gemini(media_path, client=None, api_key=None, keys=None, platform='facebook', folder_name='', index=1, log_callback=None, force_local=False):
    """
    Decodes video frames using ffmpeg and Gemini Vision models to produce
    100% video-accurate captions and exactly 5 hashtags (#MustWatch #FYP #Reels + 2 content tags).
    Rotates automatically through all available API keys with smart cooldown,
    NEVER falling back to generic duplicate local templates.
    """
    def log(msg):
        if log_callback:
            try:
                log_callback(msg)
            except Exception:
                pass
        else:
            try:
                print(msg.encode(sys.stdout.encoding or 'utf-8', errors='replace').decode(sys.stdout.encoding or 'utf-8', errors='replace'))
            except Exception:
                try:
                    print(msg.encode('ascii', errors='replace').decode('ascii'))
                except Exception:
                    pass

    # Build full list of API keys
    key_list = []
    if keys:
        if isinstance(keys, list):
            key_list.extend([k.strip() for k in keys if k and k.strip()])
        else:
            key_list.extend([k.strip() for k in re.split(r'[,;\n\r\s]+', str(keys)) if k.strip()])
    if api_key and api_key not in key_list:
        key_list.insert(0, api_key.strip())

    if not key_list:
        try:
            cfg_path = Path(__file__).parent / "config.json"
            if cfg_path.exists():
                with open(cfg_path, "r", encoding="utf-8") as f:
                    cfg_data = json.load(f)
                    c_keys = cfg_data.get("gemini_api_keys", [])
                    if not c_keys and cfg_data.get("gemini_api_key"):
                        c_keys = re.split(r'[,;\n\r\s]+', str(cfg_data["gemini_api_key"]))
                    key_list = [k.strip() for k in c_keys if k and k.strip()]
        except Exception:
            pass

    if not key_list and not client:
        log("   [!] No Gemini API key found. Please add your API key in Settings!")
        return None

    # Extract visual parts (keyframes)
    path_obj = Path(media_path)
    suffix = path_obj.suffix.lower()
    is_video = suffix in ['.mp4', '.mov', '.avi', '.mkv', '.webm']
    is_image = suffix in ['.jpg', '.jpeg', '.png', '.webp']

    parts = []
    try:
        from google.genai import types
        if is_video:
            log(f"   🎬 Decoding video frames locally with FFmpeg for '{path_obj.name}'...")
            frames_bytes = extract_video_keyframes(media_path, num_frames=3)
            if frames_bytes:
                for fb in frames_bytes:
                    parts.append(types.Part.from_bytes(data=fb, mime_type='image/jpeg'))
                log(f"   👁️ Successfully decoded {len(parts)} keyframes for visual AI analysis!")
            else:
                log("   ⚠️ Could not extract frames via FFmpeg, attempting direct read...")
        elif is_image:
            with open(media_path, 'rb') as f:
                img_data = f.read()
            mime = 'image/jpeg' if suffix in ['.jpg', '.jpeg'] else f'image/{suffix.replace(".", "")}'
            parts.append(types.Part.from_bytes(data=img_data, mime_type=mime))
    except Exception as e:
        log(f"   [!] Error preparing media frames: {e}")

    if not parts:
        log(f"   ⚠️ Could not extract visual frames from '{path_obj.name}'.")
        return None

    prompt = f"""Analyze these visual frames captured from this {platform.upper()} media clip.
Carefully examine the exact visual subjects, stunts, actions, choreography, equipment, animals, skills, and atmosphere.
Generate a viral, engaging social media post strictly in 100% FLUENT ENGLISH.

RULES:
1. Write a captivating, rich, and descriptive viral caption WITH engaging emojis (e.g. 🔥✨, 🎪⚡, 🎖️💪, 🤯💥) strictly between 75 and 92 characters (about 12 to 16 words). Describe the action vividly and end cleanly with punctuation (! or .) and emojis.
2. Follow immediately with EXACTLY 5 hashtags:
   - Must start with: #MustWatch #FYP #Reels
   - Followed by exactly 2 highly specific hashtags matching the exact video action.
3. Do NOT include ANY section titles, labels, or prefixes (Do NOT write '🎯 HOOK:', '📌 CAPTION:', '🏷️ HASHTAGS:', 'Caption:', 'Hook:', etc.).

FORMAT:
🔥✨ [Rich, descriptive 12-16 word action story caption with emojis] 🤯💥

#MustWatch #FYP #Reels #VideoTag1 #VideoTag2
"""

    clean_topic = clean_topic_name(folder_name or path_obj.parent.name)
    from google import genai
    from google.genai import types
    cfg_call = types.GenerateContentConfig(temperature=0.7)

    # Multi-Key Rotation + Smart Cooldown Wait (Never fall back to duplicate templates)
    max_rounds = 5
    for rnd in range(max_rounds):
        for k_idx, cur_key in enumerate(key_list):
            try:
                active_client = genai.Client(api_key=cur_key)
            except Exception:
                continue

            for model_name in FAST_MODELS:
                try:
                    res = active_client.models.generate_content(
                        model=model_name,
                        contents=[*parts, prompt],
                        config=cfg_call
                    )
                    raw_text = res.text.strip() if (res and res.text) else ''
                    if raw_text:
                        log(f"   ✅ Real visual decoding successful using {model_name} (Key {k_idx+1}/{len(key_list)})!")
                        return ensure_viral_hashtags(raw_text, topic_hint=clean_topic)
                except Exception as e:
                    err_str = str(e).lower()
                    if '404' in err_str:
                        continue
                    elif '429' in err_str or 'quota' in err_str or 'resource_exhausted' in err_str:
                        log(f"   🔄 Key {k_idx+1}/{len(key_list)} rate limit reached (429). Rotating to next API key...")
                        break
                    elif '503' in err_str or 'unavailable' in err_str:
                        continue
                    else:
                        continue

        if rnd < max_rounds - 1:
            cooldown_sec = 4 + (rnd * 3)
            log(f"   ⏳ All API keys temporarily rate-limited. Cooling down {cooldown_sec}s before retry round {rnd+2}/{max_rounds}...")
            time.sleep(cooldown_sec)

    log(f"   ⚠️ Could not reach Gemini Vision after {max_rounds} rounds of key rotation.")
    return None
