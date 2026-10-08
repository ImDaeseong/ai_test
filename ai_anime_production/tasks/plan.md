# Plan: audio-derived beat synchronization

1. Add a pure PCM beat analyzer and synthetic-pulse test; confirm the test fails before implementation, then passes.
2. Add the `ffmpeg` decoding adapter and `input/` audio import path; verify a generated WAV traverses the real import chain.
3. Carry beat timestamps through manifest types and scene props; verify TypeScript and manifest assertions.
4. Select measured timestamps in motion generation with BPM fallback only for audio-free input; verify targeted assertions and the existing suite.
5. Run the project regression commands and update the project HANDOFF.

Retry limit: two fixes per failing gate. HOLD on a third failure or unavailable local decoder.
