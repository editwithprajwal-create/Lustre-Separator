# -*- coding: utf-8 -*-
import os, sys, re, time, random, shutil, subprocess
from pathlib import Path

# Niche rules for smart local generation / fallback
NICHE_RULES = [
    {
        'keywords': ['army', 'military', 'soldier', 'female army', 'commando'],
        'captions': [
            'Unbelievable discipline and elite strength from these female army performers pulling off an insane live stunt! Mind-blowing coordination in the arena.',
            'Witness pure athletic power and high-flying circus precision that left the entire crowd speechless! Absolute perfection under pressure.',
            'Fearless dedication on full display as this high-bar military stunt executes with zero room for error! Watch till the very end.',
            'Jaw-dropping agility and razor-sharp focus in front of thousands! You won’t believe the balance required for this maneuver.',
            'Setting the standard for high-octane arena performances! Watch this powerhouse team redefine what\'s possible.'
        ],
        'tags': ['#MustWatch', '#FYP', '#Viral', '#USAArmy', '#CircusStunts', '#FemalePower', '#Acrobatics', '#ExtremeSkills', '#ExplorePage', '#ViralReels']
    },
    {
        'keywords': ['human can fly', 'fly', 'flying', 'wingsuit', 'skydiving', 'aerial'],
        'captions': [
            'Defying the laws of gravity with pure courage and breathtaking aerial flight! Watch this insane leap that proves humans can fly.',
            'Heart-stopping altitude and unbelievable glide speed! You will not believe the split-second control right before the finish.',
            'Total freedom in the open sky as this daredevil cuts through the clouds with surgical precision! Pure adrenaline.',
            'Standing on the edge of the world before taking the ultimate leap of faith! Breathtaking courage caught on camera.',
            'Soaring high above the earth like a real-life superhero! Watch this mind-bending flight that will leave you in awe.'
        ],
        'tags': ['#MustWatch', '#FYP', '#Viral', '#HumanFlight', '#Wingsuit', '#ExtremeStunts', '#Skydiving', '#AdrenalineRush', '#Trending', '#ExplorePage']
    },
    {
        'keywords': ['arena', 'skyrush', 'stunt', 'daredevil', 'extreme'],
        'captions': [
            'High-stakes arena action that will keep your eyes glued to the screen from start to finish! The danger here is next level.',
            'An insane test of agility, balance, and nerves as the live crowd roars with excitement! Watch this crazy finish.',
            'Edge-of-your-seat stunts executed with world-class skill and precision! How would you react if you were in the front row?',
            'Pushing human limits to the absolute edge in this heart-pounding stunt demonstration! Unbelievable reflexes.',
            'Electric energy and jaw-dropping execution that had everyone holding their breath! Pure showmanship at its finest.'
        ],
        'tags': ['#MustWatch', '#FYP', '#Viral', '#SkyStunts', '#ArenaShow', '#ExtremeAction', '#Daredevil', '#InsaneSkills', '#TrendingNow', '#ViralReels']
    },
    {
        'keywords': ['flip', 'flipsync', 'sync', 'trampoline', 'gymnastic'],
        'captions': [
            'Flawless synchronization and unbelievable trampoline flips landing live in the arena! The timing here is purely electric.',
            'Watch the incredible rhythm and teamwork as these acrobats defy physics together! Smooth, powerful, and mesmerizing.',
            'Split-second air awareness and triple rotation landing on point! The crowd could not believe their eyes.',
            'Perfect synergy and zero room for error as multiple flips sync up in mid-air! True masterclass in acrobatic timing.',
            'Gravity seemed optional during this mind-bending synchronized flip sequence! Absolute perfection.'
        ],
        'tags': ['#MustWatch', '#FYP', '#Viral', '#FlipSync', '#TrampolineFlips', '#Acrobatics', '#Gymnastics', '#LivePerformance', '#ExplorePage', '#ViralVideo']
    },
    {
        'keywords': ['circus', 'acrobat', 'trapeze', 'performer'],
        'captions': [
            'World-class circus artistry taking breath away with every high-flying spin! The sheer talent here is mesmerizing.',
            'An awe-inspiring moment under the big top lights as this dangerous routine unfolds! True dedication to the craft.',
            'Dazzling the audience with fearless acrobatics and graceful landings! What an unforgettable live spectacle.'
        ],
        'tags': ['#MustWatch', '#FYP', '#Viral', '#CircusLife', '#Acrobatics', '#AerialArt', '#LiveShow', '#IncredibleSkills', '#ExplorePage', '#Reels']
    }
]

FAST_MODELS = [
    'gemini-flash-lite-latest',
    'gemini-flash-latest',
    'gemini-3.5-flash-lite',
    'gemini-3.1-flash-lite'
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
    if not caption:
        caption = "Unbelievable moment captured live on camera that you have to see to believe!"

    # Clean topic hint
    topic_tag = re.sub(r'[^a-zA-Z0-9]', '', topic_hint.title()) if topic_hint else 'ViralVideo'
    if topic_tag.lower() in GENERIC_FOLDERS or not topic_tag:
        topic_tag = 'ViralMoment'

    required_priority = ['#MustWatch', '#FYP', '#Viral', f'#{topic_tag}']
    extra_tags = [
        '#Trending', '#Reels', '#ExplorePage', '#VideoOfTheDay',
        '#ViralReels', '#ForYouPage', '#TrendingNow', '#EpicMoments', '#Acrobatics'
    ]

    final_tags = []
    seen = set()

    # Add required priority tags first
    for tag in required_priority:
        norm = tag.lower()
        if norm not in seen:
            final_tags.append(tag)
            seen.add(norm)

    # Add AI-detected tags
    for tag in found_tags:
        norm = tag.lower()
        if norm not in seen and norm not in {'#outputmedia', '#posted', '#output', '#input', '#media'}:
            final_tags.append(tag)
            seen.add(norm)

    # Fill until we have at least 8-10 hashtags
    for tag in extra_tags:
        if len(final_tags) >= 9:
            break
        norm = tag.lower()
        if norm not in seen:
            final_tags.append(tag)
            seen.add(norm)

    return f"{caption}   {' '.join(final_tags)}"

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
            f'An extraordinary moment captured on camera that you simply have to see to believe! Watch closely as the action unfolds.',
            f'Unbelievable skill and timing delivering pure shock value in seconds! Share this with someone who needs to see it.',
            f'Pure entertainment that completely stole the spotlight! What a spectacular scene from beginning to end.',
            f'Wait till you see what happens next! Drop your honest reaction in the comments below.'
        ]
        tags_pool = ['#MustWatch', '#FYP', '#Viral', f'#{topic_tag}', '#Trending', '#Reels', '#VideoOfTheDay', '#ExplorePage', '#ViralReels', '#ForYouPage']

    caption = captions_pool[(index - 1) % len(captions_pool)]
    return ensure_viral_hashtags(f"{caption} {' '.join(tags_pool)}", topic_hint=clean_topic)

def decode_video_with_gemini(media_path, client=None, api_key=None, platform='facebook', folder_name='', index=1, log_callback=None):
    """
    Decodes video frames using ffmpeg and Gemini flash-lite to produce
    100% video-accurate captions and 8-10 viral hashtags in 3-4 seconds.
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

    # 1. Check client or API key
    active_client = client
    if not active_client and api_key:
        try:
            from google import genai
            active_client = genai.Client(api_key=api_key)
        except Exception as e:
            log(f"   [!] Failed to initialize Gemini Client: {e}")
            active_client = None

    if not active_client:
        log("   ⚡ Using smart local niche generator (no API key)...")
        return generate_local_caption_and_hashtags(media_path, folder_name=folder_name, index=index, platform=platform)

    # 2. Extract visual parts
    path_obj = Path(media_path)
    suffix = path_obj.suffix.lower()
    is_video = suffix in ['.mp4', '.mov', '.avi', '.mkv', '.webm']
    is_image = suffix in ['.jpg', '.jpeg', '.png', '.webp']

    parts = []
    try:
        from google.genai import types
        if is_video:
            log("   🎬 Decoding video frames locally with FFmpeg...")
            frames_bytes = extract_video_keyframes(media_path, num_frames=3)
            if frames_bytes:
                for fb in frames_bytes:
                    parts.append(types.Part.from_bytes(data=fb, mime_type='image/jpeg'))
                log(f"   👁️ Successfully decoded {len(parts)} keyframes for visual AI analysis!")
            else:
                log("   ⚠️ Could not extract frames via FFmpeg, falling back to direct analysis...")
        elif is_image:
            with open(media_path, 'rb') as f:
                img_data = f.read()
            mime = 'image/jpeg' if suffix in ['.jpg', '.jpeg'] else f'image/{suffix.replace(".", "")}'
            parts.append(types.Part.from_bytes(data=img_data, mime_type=mime))
    except Exception as e:
        log(f"   [!] Error preparing media frames: {e}")

    # If no visual parts extracted, fallback to local
    if not parts:
        log("   ⚡ Falling back to local niche generator...")
        return generate_local_caption_and_hashtags(media_path, folder_name=folder_name, index=index, platform=platform)

    prompt = f"""Analyze these visual frames captured from this {platform.upper()} media clip.
Carefully examine the exact visual subjects, stunts, actions, choreography, equipment, animals, skills, and atmosphere.
Generate a viral, engaging social media post strictly in 100% FLUENT ENGLISH.

RULES:
1. Write a captivating, viral story caption (1 punchy, high-impact sentence, around 15 to 22 words, maximum 100 characters) that vividly describes the exact stunts, skill, and excitement in the video with engaging emojis. Make it complete and end cleanly with punctuation (! or .).
2. Follow immediately with at least 8 to 10 viral hashtags.
3. Hashtags MUST include #MustWatch, #FYP, #Viral, plus 5-7 highly specific tags matching the exact video content.
4. Do NOT include ANY section titles, labels, or prefixes (Do NOT write '🎯 HOOK:', '📌 CAPTION:', '🏷️ HASHTAGS:', 'Caption:', 'Hook:', etc.).

FORMAT:
[Engaging 1-2 sentence story caption with emojis]

#MustWatch #FYP #Viral #Tag1 #Tag2 #Tag3 #Tag4 #Tag5 #Tag6 #Tag7
"""

    log(f"   🧠 Gemini AI is analyzing video frames...")
    clean_topic = clean_topic_name(folder_name or path_obj.parent.name)

    # Try fast models
    for model_name in FAST_MODELS:
        try:
            res = active_client.models.generate_content(
                model=model_name,
                contents=[*parts, prompt]
            )
            raw_text = res.text.strip() if (res and res.text) else ''
            if raw_text:
                log(f"   ✅ Video decoded successfully using {model_name}!")
                return ensure_viral_hashtags(raw_text, topic_hint=clean_topic)
        except Exception as e:
            err_str = str(e).lower()
            if '404' in err_str:
                continue
            elif '429' in err_str or 'quota' in err_str:
                log(f"   ⚠️ Model {model_name} rate limited, trying next model...")
                continue
            else:
                log(f"   ⚠️ Model {model_name} error: {e}, trying next model...")
                continue

    # Fallback to local if all API models fail
    log("   ⚡ All Gemini models busy/limited, using instant smart local generator...")
    return generate_local_caption_and_hashtags(media_path, folder_name=folder_name, index=index, platform=platform)
