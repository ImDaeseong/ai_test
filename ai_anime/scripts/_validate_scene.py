import json, re, sys
sys.stdout.reconfigure(encoding='utf-8')

with open("storyboard/scene_list.json", encoding="utf-8") as f:
    data = json.load(f)

issues = []
for s in data.get("scenes", []):
    sn = s["scene_number"]

    # Raw color check: all fields except lyric_visual_idea (which is lyric text)
    for field in ["lighting", "movement", "video_prompt", "scene_action"]:
        val = s.get(field, "")
        if "neon magenta" in val.lower() or "cyber pink" in val.lower():
            issues.append(f"Sc{sn:02d}.{field}: RAW COLOR")

    # Double word check: lighting only (CLAUDE.md spec)
    # video_prompt/lyric_visual_idea contain lyric text which can have intentional repetition
    lighting = s.get("lighting", "")
    m = re.search(r"(\b\w+\b) \1\b", lighting)
    if m:
        issues.append(f"Sc{sn:02d}.lighting: DOUBLE WORD [{m.group(0)}]")

    # Symbolism raw color
    for sym in s.get("symbolism", []):
        if "neon magenta" in sym.lower() or "cyber pink" in sym.lower():
            issues.append(f"Sc{sn:02d}.symbolism: RAW COLOR [{sym}]")

    # Bracket production note in lyric_visual_idea
    lyric = s.get("lyric_visual_idea", "")
    bracket_only = re.search(r"^\s*(lyric cue:|music cue:)?\s*\[[\w\s\-\d]+\]\s*$", lyric)
    if bracket_only:
        issues.append(f"Sc{sn:02d}: bracket-only lyric [{lyric[:80]}]")

    # tempo unknown
    rv = s.get("video_rhythm", "")
    if "tempo unknown" in rv.lower():
        issues.append(f"Sc{sn:02d}: tempo unknown in rhythm")

print("=== scene_list issues:", issues if issues else "none")
print()

# Chorus action diversity check
chorus_scenes = [s for s in data["scenes"] if "chorus" in s["music_section"].lower()]
chorus_actions = [s.get("scene_action", "") for s in chorus_scenes]
dupes = len(chorus_actions) > 1 and len(set(chorus_actions)) < len(chorus_actions)
if dupes:
    print("=== CHORUS ACTION DUPLICATES:")
    for s in chorus_scenes:
        print(f"  Sc{s['scene_number']:02d}: {s.get('scene_action','')[:80]}")
else:
    n = len(chorus_actions)
    print(f"=== Chorus actions ({n} scene{'s' if n != 1 else ''}): all unique")
    for s in chorus_scenes:
        print(f"  Sc{s['scene_number']:02d}: {s.get('scene_action','')[:80]}")
