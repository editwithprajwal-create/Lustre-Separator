# -*- coding: utf-8 -*-
import os, re, random
from pathlib import Path

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

def clean_topic_name(folder_or_name):
    raw = str(folder_or_name).replace('\\', '/').split('/')[-1]
    raw = re.sub(r'\.[a-zA-Z0-9]+$', '', raw)
    raw = re.sub(r'[\-_]+', ' ', raw)
    raw = re.sub(r'\b(?:400|Full|Prompts?|201|to|600|9x16|16x9|1080p|4k|Generated|video|no|watermark|live)\b', '', raw, flags=re.I)
    raw = re.sub(r'\s+', ' ', raw).strip()
    return raw or 'Viral Video'

def generate_local_caption_and_hashtags(media_path, folder_name='', index=1, platform='facebook'):
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
        topic_tag = re.sub(r'[^a-zA-Z0-9]', '', clean_topic.title()) or 'ViralMoment'
        captions_pool = [
            f'An extraordinary moment captured on camera that you simply have to see to believe! Watch closely as the action unfolds.',
            f'Unbelievable skill and timing delivering pure shock value in seconds! Share this with someone who needs to see it.',
            f'Pure entertainment that completely stole the spotlight! What a spectacular scene from beginning to end.',
            f'Wait till you see what happens next! Drop your honest reaction in the comments below.'
        ]
        tags_pool = ['#MustWatch', '#FYP', '#Viral', f'#{topic_tag}', '#Trending', '#Reels', '#VideoOfTheDay', '#ExplorePage', '#ViralReels', '#ForYouPage']

    caption = captions_pool[(index - 1) % len(captions_pool)]

    final_tags = []
    seen = set()
    for tag in tags_pool:
        if tag.lower() not in seen:
            final_tags.append(tag)
            seen.add(tag.lower())

    backup_pool = ['#MustWatch', '#FYP', '#Viral', '#Trending', '#ViralReels', '#ExplorePage', '#Reels', '#VideoOfTheDay', '#ForYouPage', '#TrendingNow']
    for btag in backup_pool:
        if len(final_tags) >= 8:
            break
        if btag.lower() not in seen:
            final_tags.append(btag)
            seen.add(btag.lower())

    hashtags_str = ' '.join(final_tags)
    return f'{caption}   {hashtags_str}'
