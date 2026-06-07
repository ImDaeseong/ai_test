# AI Anime Validation Report

Date: 2026-06-07

## Result

- Automated P0/P1 defects: 0
- Unit tests: 66 passed
- Config validation: 0 errors, 0 warnings
- Existing output scan: 214 passed, 0 failed
- Existing output scan duration: 121.7 seconds
- Regression: 3 passed, 0 failed, 32 skipped
- Actual generated media: 0 images, 0 videos

## Changes Made

- Split `__validate_all.py` into a fast read-only output scan and explicit `--regenerate` mode.
- Added parallel read validation with `--workers`, plus `--song` and `--limit` selectors.
- Installed FFmpeg 8.1.1.
- Changed audio-dependent regression fixtures with missing audio from false failures to explicit skips.
- Added three unit tests for regression audio-asset detection.

## FFmpeg Smoke Test

- `그래서 더 좋아.mp3`: duration 179.359979 seconds, mean -15.6 dB, max -1.6 dB
- `UPGRADE.wav`: duration 242.952 seconds, mean -14.5 dB, max 0.0 dB

## Remaining Holds

- Thirty audio-dependent fixtures reference legacy source folders whose current replacements contain only `raw_song.txt`.
- Two fixtures have no source: `커피 한 잔`, `별이 지는 밤`.
- Q3/Q4 human visual review is not executable until representative images and clips are generated.

These holds are missing-test-asset issues, not confirmed code defects.
