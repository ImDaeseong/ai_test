import re, os, sys
sys.stdout.reconfigure(encoding='utf-8')

image_dir = "prompts/image_prompts"
results = []

for fname in sorted(os.listdir(image_dir)):
    path = os.path.join(image_dir, fname)
    with open(path, encoding="utf-8") as f:
        content = f.read()

    # Raw color check
    if "neon magenta" in content.lower() or "cyber pink" in content.lower():
        results.append(f"RAW COLOR in {fname}")

    # Check no [bracket] production notes in body text (outside headings/metadata)
    lines = content.splitlines()
    for line in lines:
        if line.startswith("#") or line.startswith(">") or not line.strip():
            continue
        m = re.search(r"^\[[\w\s\-]+\]$", line.strip())
        if m:
            results.append(f"Standalone bracket note in {fname}: {line.strip()}")

    # FLUX.1: check weight syntax (should not have broken weight tokens)
    if "## FLUX.1" in content:
        flux_m = re.search(r"## FLUX\.1.*?\n(.*?)(?=\n## |\Z)", content, re.DOTALL)
        if flux_m:
            flux_body = flux_m.group(1)
            # malformed weight: double colon, unmatched paren
            bad_weights = re.findall(r"\([^)]*::[^)]*\)", flux_body)
            if bad_weights:
                results.append(f"FLUX bad weight syntax in {fname}: {bad_weights}")

    # Midjourney/Nijijourney: check --ar parameter present
    for platform in ["## Midjourney", "## Nijijourney"]:
        if platform in content:
            plat_m = re.search(re.escape(platform) + r"\n(.*?)(?=\n## |\Z)", content, re.DOTALL)
            if plat_m and "--ar" not in plat_m.group(1):
                results.append(f"{platform.strip('#').strip()} missing --ar in {fname}")

if results:
    print("=== IMAGE PROMPT ISSUES ===")
    for r in results:
        print(r)
else:
    print("=== IMAGE PROMPTS: all pass ===")
