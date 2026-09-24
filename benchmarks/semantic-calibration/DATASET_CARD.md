# Dataset Card — VoxRubric Semantic Evidence Calibration Set

**Dataset ID:** `voxrubric-semantic-calibration`  
**Version:** `1.0.0`  
**License:** Apache-2.0

## Purpose

This benchmark tests conservative semantic-evidence behavior: claimed, demonstrated, contradicted, and insufficient evidence states; transcript revisions; failed latest judge runs; superseded history; and fabricated quote rejection.

## Source policy

All traces and gold labels are synthetic and hand-authored for evaluator regression testing.

## Intended use

Use the set to verify evidence-state semantics, freshness logic, and judge-run provenance after code or model-integration changes.

## Out of scope

The gold labels are not a hiring standard and should not be interpreted as calibrated probabilities of applicant competence.

## Limitations

Coverage is deliberately narrow. The set emphasizes edge cases and lifecycle correctness rather than broad occupational or linguistic representation.
