# Handoff

## Goal

Reduce repetitive `ai-webtoon` staging by deriving reusable concert-production profiles from official real-band references without imitating artists.

## Completed

- Added 8 performance profiles and 7 official-source records.
- Added genre/BPM/mood/emotion profile scoring.
- Added deterministic per-panel camera, lighting, movement, and audience variants.
- Added safety boundaries excluding artist names, faces, logos, exact costumes, and exact stages from prompts.
- Added tests and Hermes governance documents.
- Regenerated and validated `UPGRADE`, `Off-Line`, and `Lazy Afternoon`.

## Verification

- Unit checks: 52 passed, 0 failed
- Syntax: `main.py`, `tests_unit.py` passed
- Corpus distribution: 214 songs across all 8 profiles
- Representative outputs: 3 passed folder validation
- Artist-name scan in representative panel prompts: 0 matches

## Human Review Remaining

- Compare representative generated images, not only prompt text.
- Approve visual diversity and rights-safety before public upload.

