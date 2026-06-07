# Handoff

## Goal

Add a sourced genre visual-reference layer without turning `ai_anime` into a fixed-template generator.

## Scope

- Six families: rock, acoustic/ballad, hip-hop/trap, electronic/synth, idol pop, jazz/soul
- Generalized narrative, location, camera, motion, editing, lighting, and character grammar
- Provenance retained only in config and documentation

## Verification

- Added `configs/genre_reference_profiles.json` with 8 public institutional source records.
- Added six generalized genre families covering all 20 existing genre profiles.
- Added `scripts/genre_reference.py` and integrated references into world, character, camera, motion, lighting, and transition generation.
- `python scripts/tests_unit.py`: 66 tests passed.
- `python scripts/validate_configs.py`: 0 errors, 0 warnings.
- Representative generation passed for `UPGRADE`, `100 Seconds`, `Off-Line`, `그 소녀`, `같은 하늘 다른 세상`, and `골목길 돌아서`.
- Representative output consistency: PASS 6, FAIL 0, 16 non-critical existing anchor warnings.
- All 214 current inputs map to a family: acoustic 57, hip-hop 31, rock 8, idol pop 23, jazz/soul 48, electronic 47.
- Source and institution name leakage scan: 0 matches.
- FFmpeg 8.1.1 is installed. Real MP3/WAV smoke tests returned valid durations and volume measurements.
- Regression now reports missing audio assets as skips instead of false code failures: 3 passed, 0 failed, 32 skipped. Thirty fixtures require deleted legacy audio, and `커피 한 잔`/`별이 지는 밤` have no source.
- `__validate_all.py` now scans all 214 existing outputs in parallel by default and completed in 121.7 seconds: PASS 214, FAIL 0. Expensive regeneration remains available through `python __validate_all.py --regenerate`.
- Actual media review cannot start yet because `ai_anime/output` contains 0 generated image or video files.

## Human Review

Restore representative audio fixtures when audio regression coverage is required. Generate representative images and clips, then perform originality and genre-separation review.
