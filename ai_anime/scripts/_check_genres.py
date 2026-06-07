import json, sys
sys.stdout.reconfigure(encoding='utf-8')

with open('configs/genres.json', encoding='utf-8') as f:
    data = json.load(f)

print(f"Total profiles: {len(data)}")

mojibake = []
for p in data:
    pid = p.get('id', '')
    for key in p.get('keys', []):
        # Check for replacement characters or non-printable sequences
        if '�' in key or any(ord(c) > 0xFFFF for c in key):
            mojibake.append(f"{pid}: [{key}]")
        # Also flag strings that look like garbled bytes
        encoded = key.encode('utf-8', errors='replace')
        if b'\xef\xbf\xbd' in encoded:
            mojibake.append(f"{pid}: replacement_char [{key}]")

print("mojibake keys:", mojibake[:20] if mojibake else "none")

# Also show any non-Korean, non-ASCII, non-Latin characters
unusual = []
for p in data:
    pid = p.get('id', '')
    for key in p.get('keys', []):
        # Flag keys with mixed scripts that might be encoding artifacts
        has_latin = any('a' <= c.lower() <= 'z' for c in key)
        has_hangul = any('가' <= c <= '힣' for c in key)
        has_unusual = any(c not in ' -_.,/' and not c.isalnum() and not ('가' <= c <= '힣') for c in key)
        if has_unusual and not has_hangul:
            unusual.append(f"{pid}: [{key}]")

print("unusual chars:", unusual[:10] if unusual else "none")
