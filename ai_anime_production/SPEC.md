# Audio-derived beat synchronization

## Purpose

When a music-video input contains audio, measure its tempo and beat timestamps from the audio waveform so Remotion effects follow the recording instead of a BPM number embedded in prompt text.

## Scope

- Accept at most one audio file in `input/` alongside the existing scene assets.
- Decode the audio to mono PCM with the locally installed `ffmpeg` executable.
- Estimate BPM and beat phase from an onset envelope, then produce an ordered fixed-tempo beat grid.
- Reject non-periodic input when normalized onset autocorrelation confidence is below 0.2.
- Reject audio whose duration differs from the scene-duration total by more than 0.25 seconds before copying generated assets.
- Store measured values in the source and render manifests.
- Use measured timestamps for beat pulses. Preserve the existing prompt-BPM fallback only when no audio was supplied.

Out of scope: source separation, time-varying tempo maps, downbeat/bar classification, and changing scene storyboards. `first_beat_seconds` means the first beat-grid phase, not a classified bar downbeat.

## Security and side-effect boundary

- Read only files under this project and the selected `input/` audio.
- Run the local `ffmpeg` executable without a shell.
- Write only existing generated locations under `public/assets/audio/`, `manifests/`, and test temporary directories.
- Do not upload audio or call an external service.
- HOLD when audio is supplied but decoding or beat analysis fails; do not silently substitute prompt BPM.

## Acceptance criteria

1. A synthetic 120 BPM pulse train with its first pulse at 0.25 seconds is measured within a bounded tolerance and returns increasing beat timestamps.
2. `import:input` accepts one supported audio file, rejects multiple audio files, and records measured BPM plus beat timestamps.
3. Silence, deterministic non-periodic noise, and audio/scene duration mismatch fail with explicit diagnostics.
4. `RenderManifest` carries measured beat timestamps through full-video and per-scene rendering.
5. Motion uses the measured timestamps when present and retains the prior BPM oscillator only for audio-free manifests.
6. Existing parser tests, new audio-analysis tests, TypeScript checking, and asset validation pass.

## Verification

- `npm test`
- `npm run typecheck`
- `npm run validate` with the existing audio-free fixture
- A temporary generated pulse WAV imported through the real `import:input` command

## Exit and HOLD conditions

Exit when all acceptance checks pass and the project HANDOFF records the result. HOLD after three failures of the same gate, when `ffmpeg` is unavailable, or when no deterministic synthetic-audio result can be produced.
