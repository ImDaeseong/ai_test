# AI Coding Review

## Review Scope

- The engine remains data-driven.
- Classification and generation-reference responsibilities are separated.
- No title-based or folder-based branching is introduced.
- No external package or runtime network dependency is added.
- Existing configs remain compatible.

## Rights And Safety

- Sources are provenance only.
- Generated prompts use generalized visual grammar.
- Generated prompts prohibit recognizable artists, copyrighted characters, logos, exact costumes, signature props, and exact stage replication.
- Source names and URLs are not copied into generated outputs.

## Operational Review

- Missing or malformed optional reference data falls back to existing behavior.
- Selection is deterministic through the existing SHA-256 seed helpers.
- Config validation checks required fields and source references.

## Human Hold

- Actual generated images and clips need side-by-side originality review.

## Verification

- No new package or network runtime dependency
- No song-title branching
- All 20 genre profiles mapped
- 63 unit tests passed
- Config validation passed
- Six representative outputs passed consistency validation
- Source-name and secret-pattern scans returned zero matches
