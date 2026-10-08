# Plan: render layout verification

1. Add failing rectangle-validation tests for clipping and overlap.
2. Implement the pure validator and connect it to browser-computed lyric rectangles.
3. Add a render-sampling command for both compositions at five timeline positions.
4. Run parser/layout tests and type checking, then attempt the real render evidence command.
5. Document PASS or HOLD and update the project HANDOFF.

Retry limit: two fixes per gate; HOLD on the third failure or missing required media/browser.
