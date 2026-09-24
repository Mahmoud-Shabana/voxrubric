# VoxRubric v0.5.0 Release Plan

Status: active  
Baseline before this release pass: `bcfd2966`  
Current development line: `main`

This file is the canonical release checklist. README roadmap items are descriptive; this checklist is the source of truth for what should be worked next.

## Rules

1. Do not re-implement a capability already present on `main`.
2. Before starting a feature, search code, tests, docs, and recent commits for an existing implementation.
3. A feature is complete only when implementation, tests, and documentation agree.
4. Do not create commits solely to increase commit count.
5. Voice, Arena, Nora integration, HTML reporting, semantic calibration, and bootstrap confidence intervals are frozen unless a regression exposes a concrete gap.

## Confirmed complete / frozen

- Nora HTTP Arena adapter
- YAML Arena configuration
- repeated-run path stability
- HTML Arena and trace-diff reports
- semantic calibration benchmark packs
- VAD endpoint recovery metrics
- voice transport continuity metrics
- audit-chain integrity checks
- bootstrap 95% confidence intervals for Arena metric aggregates
- hosted OpenAI-compatible JudgeProvider reference adapter

## Release gates

### Gate 1 — Hosted judge hardening

- [x] OpenAI-compatible hosted JudgeProvider
- [x] reject unknown rubric dimensions
- [x] reject duplicate rubric dimensions
- [x] require every rubric dimension exactly once
- [x] require evidence to reference candidate turns
- [x] require literal evidence quotes
- [x] preserve provider/model metadata
- [ ] run complete regression suite when CI execution is available

### Gate 2 — Semantic evaluation depth

- [ ] local-model JudgeProvider reference adapter
- [ ] semantic follow-up quality evaluator
- [ ] multi-judge semantic evidence disagreement analysis

### Gate 3 — Benchmark depth

- [ ] ASR-preservation benchmark pack
- [ ] richer role/domain benchmark packs
- [ ] versioned benchmark dataset metadata and dataset cards

### Gate 4 — Integration and release regression

- [ ] end-to-end Nora export -> VoxRubric evaluation regression fixture
- [ ] verify CLI eval, benchmark, Arena, and HTML report paths together
- [ ] update release changelog
- [ ] bump package version to 0.5.0 only after all required gates pass

## Explicitly not next

Do not spend a development cycle rebuilding:

- Nora Arena adapter
- HTML comparison reporting
- statistical confidence intervals
- VAD recovery metrics
- semantic calibration packs

Those capabilities already exist on `main`.
