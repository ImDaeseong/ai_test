# Pre-Deploy

## Automated

- [x] unit tests pass: 66 tests
- [x] config validation passes: 0 errors, 0 warnings
- [x] FFmpeg 8.1.1 installed; MP3/WAV duration and loudness smoke tests pass
- [x] regression runner distinguishes missing audio assets from code failures: 3 pass, 0 fail, 32 skip
- [x] six representative songs generate successfully
- [x] six-song output consistency: PASS 6, FAIL 0
- [x] source-name leakage scan returns zero
- [x] Python syntax checks pass in staging
- [x] `__validate_all.py` existing-output scan: PASS 214, FAIL 0 in 121.7 seconds
- [x] full regeneration moved behind explicit `--regenerate`; it is no longer part of the fast validation path

## Asset Holds

- [ ] restore audio assets for 30 audio-dependent fixtures
- [ ] restore the two missing legacy fixture sources: `커피 한 잔`, `별이 지는 밤`
- [ ] generate representative images and clips; current `output` contains 0 image/video files

## Human Hold

- [ ] six genre families are visually distinguishable
- [ ] lyrics remain more important than reference grammar
- [ ] no recognizable artist, logo, costume, character, prop, or stage imitation

## Rollback

Remove the new config and module, then restore the integration scripts listed in `PROJECT_START.md`.
