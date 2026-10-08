# Render review

## Automated gates

- Current lyric contrast: at least 7:1 against the lyric panel under the brightest possible media background.
- Context lyric contrast: at least 4.5:1 under the same condition.
- Readability: at most 80 graphemes per lyric line and 20 graphemes per second.
- Layout: visible lyric boxes remain inside the composition and do not overlap.
- Evidence: `npm run verify:render` replaces stale verification PNGs and renders five current samples for each composition.

## Human review record — 2026-10-08

Temporary neutral-background WAV/LRC fixture, horizontal and vertical midpoint samples:

- PASS — current, previous, and next lines have an unambiguous hierarchy.
- PASS — the dark lyric panel separates all text from the background.
- PASS — padding, rounded panel boundary, and waveform spacing are visually balanced in both aspect ratios.
- PASS — no clipping, collision, or distracting transition artifact is visible.
- NOT EVALUATED — lyric meaning, emotional fit, translation accuracy, and suitability for a specific production background.

Repeat the human review with production media whenever the background, font, lyric wording, or motion treatment changes. Semantic correctness requires a reviewer who understands the song and target language.
