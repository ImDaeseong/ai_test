# HANDOFF

## 2026-10-08 — render layout verification

- Goal: detect lyric clipping/overlap during real Remotion rendering and retain representative frame evidence.
- Changed: added a pure rectangle validator, browser-computed lyric bounds, unit tests, and `npm run verify:render` for five horizontal plus five vertical PNG samples.
- Verification: `npm test` (19/19), `npm run typecheck`, and a temporary four-second WAV/LRC fixture render all passed. The first render exposed and then guarded against an incorrect viewport/canvas coordinate comparison.
- Output: sampled PNGs are under ignored `out/verification/`; temporary input fixture was removed after the run.
- Remaining risk: rectangle checks do not judge contrast, typography quality, or semantic readability; those remain human visual-review items. A normal verification run requires project media and local Chrome.
- Next step: run `npm run verify:render` again whenever production media or lyric styling changes, then inspect the ten PNGs.

## 2026-10-08 — contrast, readability, and dependency follow-up

- Added a dark lyric panel and raised context opacity; deterministic tests establish at least 7:1 current-text and 4.5:1 context-text contrast under the brightest possible media background.
- Added pre-render limits of 80 graphemes per line and 20 graphemes per second, with regression tests.
- `verify:render` now deletes only its own prior sample PNGs before rendering so evidence cannot mix across runs.
- `npm audit fix` updated affected transitive packages; `npm audit --json` reports zero vulnerabilities.
- Human review of horizontal and vertical fixture samples is recorded in `RENDER_REVIEW.md`. Meaning, translation, emotional fit, and production-background aesthetics remain production-media review responsibilities.
