# Release decision — 2026-10-09

## Decision

`NOT APPROVED FOR PUBLICATION`

## Evidence

- Technical contract: PASS — 1920×1080, H.264/AAC, 195.967 seconds.
- Automated quality: PASS — black 0%, silence 0%, freeze 11.24%.
- Visual-diversity remediation: PASS — continuous non-saturating zoom/pan reduced freeze from 72.0% to 11.24%.
- Rights evidence: FAIL — four local inputs exist, but no receipt, licence, ownership record, or other evidence file is present.

## Rationale

Technical and measurable creative-quality gates are satisfied. Publication remains blocked because the repository cannot establish ownership, commercial-use permission, or attribution obligations for the actual audio, image, and lyrics. Hermes does not infer legal rights from file possession.

## Reconsideration condition

Create local `release-review.json` from the example, attach evidence files for every publication asset, record their SHA-256 values, and run `npm run validate:release`. Publication may be reconsidered only after that command passes without HOLD or FAIL.
