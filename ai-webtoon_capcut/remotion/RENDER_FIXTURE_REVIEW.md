# 30-second renderer fixture review

Date: 2026-10-09

## Deterministic evidence

- Direct renderer command: `npm run render:fixture`
- Integrated command: `uv run webtoon-capcut render --timeline ... --audio ... --output ... --remotion-dir remotion --json`
- Composition: `WebtoonVideo`
- Output: H.264 video + AAC audio, 960×540, 30 fps
- Duration: 30.016 seconds (900 frames)
- SHA-256: `f7c5ffc6d66973b55df326f68b307109eae9007d88fb4fd05dbc8f5ed8d4648f`
- TypeScript: PASS
- npm audit: 0 vulnerabilities

The MP4 and extracted PNGs live under ignored `out/`; rerun the command to reproduce them.

## Visual sample review

Frames at 5, 15, and 25 seconds were opened at original resolution. Each showed the expected panel, section label, title, safe margins, and distinct motion state without clipping, overlap, or missing media. This proves the fixture composition path, not production artwork quality.

## Remaining production gate

The integrated CLI render produced H.264/AAC at 1920×1080, 30fps, 30.016 seconds. It staged private inputs under an ignored job directory, rendered to a temporary MP4, atomically replaced the target, and removed both staging and props. SHA-256: `cce6c0ec96258c0d3dac28cdddc1a140550621b259b285e429df149e73723e7b`.

A real-song 1080p render still needs Python-generated timeline data plus complete licensed media. No audio or full panel set was present in the scanned local song folders, so synchronization, crop choices, subtitles, rights, and final edit quality remain a person-review HOLD.
