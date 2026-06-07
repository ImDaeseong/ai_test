# Project Start

## Basic Information

- Project: AI Anime MV Builder genre reference layer
- Purpose: enrich song-specific anime MV prompts with sourced, generalized visual grammar for six genre families.
- Type: personal project, existing feature enhancement
- Started: 2026-06-07

## Data And Security

- Classification: public
- Sources: public museum, archive, and music-institution pages only
- No API keys, credentials, customer data, company data, or private URLs
- Artist and work names remain provenance metadata and must not appear in generated prompts

## Architecture

- Python standard library and JSON configs
- `configs/genre_reference_profiles.json` stores provenance and generalized genre visual grammar
- `scripts/genre_reference.py` selects and exposes the reference profile
- Existing genre classification remains in `configs/genres.json`
- Existing palette, character, scene, and platform generators remain authoritative

## Decisions

1. Separate classification keywords from generation references.
   - Reason: `genres.json` already mixes 2,000+ matching keys with prompt content.
   - Rejected: expanding each existing genre object with more source-derived fields.
2. Use generalized visual grammar, not imitation.
   - Reason: preserve originality and reduce artist, likeness, costume, logo, and signature-stage copying risk.
   - Rejected: naming artists or works in generated prompts.
3. Start with six broad families.
   - Reason: cover the dominant input distribution before expanding all 20 profiles.

## Rollback

- Remove `configs/genre_reference_profiles.json` and `scripts/genre_reference.py`.
- Restore the previous versions of the four integration scripts.
- Existing `genres.json` and generated input data require no migration.

## Completion

- Config schema validation passes.
- Unit tests cover mapping, determinism, provenance separation, and prompt integration.
- Existing regression behavior remains stable except for intentional visual-language enrichment.
- Representative rock, acoustic, hip-hop, electronic, idol-pop, and jazz/soul prompts contain family-specific language.
- Generated prompts contain no source artist or work names.
