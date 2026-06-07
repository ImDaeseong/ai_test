# Testing Done Criteria

## Acceptance Conditions

1. Given a song matched to one of the six supported genre families, when its visual world is created, then family-specific location, camera, motion, lighting, transition, and character guidance is available.
2. Given the same song, when generation is repeated, then reference choices are deterministic.
3. Given generated prompts, when provenance names are scanned, then no artist, group, exhibition, or work name from the source metadata appears.
4. Given an unsupported profile, when generation runs, then existing behavior continues without failure.

## Automated Checking

- `python scripts/tests_unit.py`
- `python scripts/validate_configs.py`
- `python scripts/run_regression.py`
- representative six-family pipeline generation and folder validation
- source-name leakage scan
- repeated-location and family-distribution analysis

## Human Testing

- Q3: compare six representative outputs side by side for visible genre separation.
- Q3: confirm reference guidance supports the song rather than overriding lyrics.
- Q4: confirm no recognizable face, logo, exact costume, signature prop, or exact stage replication.

## Done

- P0/P1 automation defects: zero
- Existing parser and platform-format checks remain passing
- Q3/Q4 remain a release hold until actual generated images and clips are reviewed
