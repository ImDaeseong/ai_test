# Render layout verification

## Purpose

Render representative horizontal and vertical lyric-video frames and fail when measured lyric boxes leave the canvas or overlap one another.

## Scope

- Validate browser-computed lyric element rectangles inside the Remotion composition.
- Render deterministic PNG samples at the beginning, quarter points, midpoint, and end of both compositions.
- Store sample evidence under `out/verification/`.

Out of scope: computer-vision aesthetic scoring and judging lyric meaning or translation accuracy.

## Security and side-effect boundary

- Read project-local media and source files only.
- Start the locally installed Remotion renderer and configured local Chrome executable.
- Write only `out/verification/` and generated `src/mediaManifest.ts`.
- HOLD when required media or Chrome is unavailable.

## Acceptance criteria

1. Pure rectangle checks reject canvas clipping and overlap with distinct diagnostics.
2. The lyric composition measures the actual browser layout on render and throws those diagnostics on failure.
3. The verification command renders five PNGs for each horizontal and vertical composition.
4. Parser tests, layout tests, type checking, and `git diff --check` pass.
5. Current/context lyric contrast meets 7:1/4.5:1 under the brightest media background, and excessive line length or reading speed fails before render.
6. Human visual review is recorded separately without presenting subjective judgment as an automated PASS.

## Verification

- `npm test`
- `npm run typecheck`
- `npm run verify:render`

## Exit and HOLD conditions

Exit when automated checks pass and PNG evidence is rendered from available media. HOLD after three failures of one gate or when media/Chrome is unavailable; retain the deterministic layout tests even if visual evidence is held.

The implementation was exercised with a temporary four-second local WAV/LRC fixture because the project had no user media. The fixture is removed after verification; future runs use the media under `public/media/`.
