import json, re, sys
sys.stdout.reconfigure(encoding='utf-8')

with open("storyboard/scene_list.json", encoding="utf-8") as f:
    data = json.load(f)

for s in data["scenes"]:
    if s["scene_number"] == 5:
        print("=== Scene 05 ===")
        print("music_section:", s.get("music_section", ""))
        print()
        print("video_prompt:", s.get("video_prompt", ""))
        print()
        print("lyric_visual_idea:", s.get("lyric_visual_idea", ""))
        print()
        print("scene_action:", s.get("scene_action", ""))
        print()
        # Find double word
        for field in ["video_prompt", "lyric_visual_idea", "scene_action", "lighting", "movement"]:
            val = s.get(field, "")
            m = re.search(r"(\b\w+\b) \1\b", val)
            if m:
                # Show surrounding context
                idx = m.start()
                print(f"DOUBLE in {field}: ...{val[max(0,idx-30):idx+60]}...")
