# Pre-Deploy Checklist

## Automated

- [x] Python syntax check
- [x] Unit and regression checks
- [x] Profile source-reference integrity
- [x] Representative song generation
- [x] Representative output folder validation
- [x] Real artist names absent from panel prompts

## Human Hold

- [ ] Compare at least three songs side by side for visible stage and camera diversity.
- [ ] Confirm no generated image copies a real face, logo, exact costume, signature prop, or exact stage.
- [ ] Confirm the original skeleton-band identity remains consistent.

## Rollback

Restore the previous `main.py` and remove `configs/band_performance_profiles.json`. Existing output folders can then be regenerated with the earlier prompt logic.

## Deploy Decision

Code is ready for local use. Public publishing remains on hold until the human checks above are completed.

