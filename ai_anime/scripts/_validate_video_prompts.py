import re, os, sys
sys.stdout.reconfigure(encoding='utf-8')

video_dir = "prompts/video_prompts"
results = []

for fname in sorted(os.listdir(video_dir)):
    path = os.path.join(video_dir, fname)
    with open(path, encoding="utf-8") as f:
        content = f.read()

    # Kling: 40-65 words, ends with ".", has conclusion trigger
    m = re.search(r"## Kling AI\n(.*?)\n\n>", content, re.DOTALL)
    if m:
        k = m.group(1).strip()
        wc = len(k.split())
        has_end = k.endswith(".")
        conclusion_triggers = ("settles", "stillness", "returns to", "fades", "comes to rest")
        has_conclusion = any(t in k.lower() for t in conclusion_triggers)
        ok = wc <= 65 and has_end and has_conclusion
        if not ok:
            results.append(f"Kling FAIL {fname}: {wc}w, ends_with_period={has_end}, has_conclusion={has_conclusion}")
            results.append(f"  body: {k[:120]}")

    # Sora: 5 sections
    for sec in ["**Scene:**", "**Cinematography:**", "**Actions:**", "**Style:**", "**Sound:**"]:
        if sec not in content:
            results.append(f"Sora missing {sec} in {fname}")

    # Runway: [camera]: lead
    m = re.search(r"## Runway\n(\[.*?\]:)", content)
    if not m:
        m2 = re.search(r"## Runway\n([^\n]{1,60})", content)
        if m2 and not m2.group(1).startswith("["):
            results.append(f"Runway missing [bracket] lead in {fname}: {m2.group(1)[:60]}")

    # Wan: negative prompt block
    if "## Wan 2.2" in content:
        wan_m = re.search(r"## Wan 2\.2\n(.*?)\n\n>", content, re.DOTALL)
        if wan_m and "Negative prompt" not in wan_m.group(1):
            results.append(f"Wan missing Negative prompt in {fname}")

    # Check no "Static shot." or "Drone shot" as Wan/Luma camera false match
    for bad in ["Static shot.", "Drone shot"]:
        if f"## Wan 2.2\n{bad}" in content or f"## Luma Dream Machine\n{bad}" in content:
            results.append(f"Camera mismatch '{bad}' in {fname}")

    # Check no "tempo unknown" in content
    if "tempo unknown" in content.lower():
        results.append(f"tempo unknown in {fname}")

    # Check no raw bracket production notes in lyric cue lines
    for line in content.splitlines():
        if "Lyric cue:" in line or "lyric cue:" in line:
            bracket_m = re.search(r"\[[\w\s\-]+\]", line)
            if bracket_m:
                results.append(f"Bracket in lyric cue in {fname}: {line[:100]}")

if results:
    print("=== VIDEO PROMPT ISSUES ===")
    for r in results:
        print(r)
else:
    print("=== VIDEO PROMPTS: all pass ===")
