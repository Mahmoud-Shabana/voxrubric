# Dataset Card — VoxRubric Adversarial Evaluator Regression Set

**Dataset ID:** `voxrubric-adversarial`  
**Version:** `1.0.0`  
**License:** Apache-2.0

## Purpose

This synthetic dataset regression-tests evaluator invariants. It includes healthy controls and deliberately broken traces for evidence grounding, rubric coverage, follow-up lineage, latency, and semantic evidence provenance.

## Source policy

All records are hand-authored synthetic fixtures. No real applicant transcripts or personal data are included.

## Intended use

Use this dataset to verify that VoxRubric catches known failure modes for the expected reason and does not regress after metric changes.

## Out of scope

Do not use these traces to estimate candidate ability, demographic effects, hiring validity, or real-world model accuracy.

## Limitations

The set is intentionally small and adversarial. It is not statistically representative of jobs, applicants, accents, languages, or production traffic.
