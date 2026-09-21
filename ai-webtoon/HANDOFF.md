# Handoff

## Goal

Reduce repetitive `ai-webtoon` staging by deriving reusable concert-production profiles from official real-band references without imitating artists.

## Completed

- Restored direct `gpt-image-2` generation in the port-5350 web viewer; the removed `ai_multi_agent` project is no longer required.
- Added a no-auto-retry OpenAI adapter, monthly 100-call guard, privacy-safe usage records, sanitized user errors, and mock regression tests.
- Generated images are saved under `output/<song>/panels/<panel>/image.png`; reference images remain local unless the user manually uploads them elsewhere.
- Verified a real OpenAI image request on 2026-09-22 using the shared private key loader; fixed production prompt parsing and isolated generated/done state per panel.
- Added 8 performance profiles and 7 official-source records.
- Added genre/BPM/mood/emotion profile scoring.
- Added deterministic per-panel camera, lighting, movement, and audience variants.
- Added safety boundaries excluding artist names, faces, logos, exact costumes, and exact stages from prompts.
- Added tests and Hermes governance documents.
- Regenerated and validated `UPGRADE`, `Off-Line`, and `Lazy Afternoon`.

## Verification

- Unit checks: 67 passed, 0 failed
- Syntax: `main.py`, `web_app.py`, `image_client.py`, `credential_loader.py`, and `budget_guard.py` passed
- Corpus distribution: 214 songs across all 8 profiles
- Representative outputs: 3 passed folder validation
- Artist-name scan in representative panel prompts: 0 matches

## Human Review Remaining

- Compare representative generated images, not only prompt text.
- Approve visual diversity and rights-safety before public upload.

