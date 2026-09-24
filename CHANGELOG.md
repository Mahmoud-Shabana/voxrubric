# Changelog

All notable VoxRubric changes are documented here.

## Unreleased — 0.5.0

### Role/domain benchmark coverage

- Added Customer Support, Data Analyst, and Site Reliability Engineering benchmark packs.
- Added bilingual Arabic/English support controls.
- Added role-specific expected failures for missing rubric coverage and broken follow-up lineage.
- Added pack-level regression coverage across all three domains.

### ASR preservation

- Added deterministic ASR preservation metric with normalized word error rate and word accuracy.
- Added job-relevant critical-term recall checks.
- Added Arabic/Latin code-switch preservation checks for mixed-language reference transcripts.
- Added an Arabic/English technical ASR benchmark pack with healthy controls and expected-failure cases.
- Added pack-level regression coverage.

### Semantic follow-up quality

- Added an opt-in `SemanticFollowUpQualityMetric` backed by any `JudgeProvider`.
- Evaluates each declared interviewer follow-up against its referenced candidate answer.
- Requires both a configurable semantic score threshold and literal evidence from the parent answer.
- Provider failures are reported as metric failures instead of crashing the evaluation run.
- Kept semantic model calls out of the deterministic default evaluator.
- Added regression coverage for strong, weak, ungrounded, failed-provider, and non-applicable cases.

### Semantic judge disagreement

- Added descriptive cross-judge disagreement analysis for both normalized scores and evidence provenance.
- Added per-dimension evidence Jaccard comparison and material-disagreement classification.
- Added default evaluator integration and regression coverage for consensus, score divergence, evidence divergence, and single-judge non-applicability.

### Local semantic judging

- Added a strict Ollama `JudgeProvider` reference adapter using the native local chat endpoint.
- Reused the hosted adapter's scorecard, dimension, and literal-evidence validation instead of maintaining two validation paths.
- Added local-model timing/token provenance when Ollama returns it.
- Added regression coverage for native request shape, custom endpoints, invalid response shapes, and fabricated evidence.
- Added `hosted` and `local` optional dependency groups.

### Hosted semantic judging

- Added a strict OpenAI-compatible `JudgeProvider` reference adapter.
- Added optional `hosted` dependency group for HTTP judge providers.
- Rejects unknown, duplicate, or omitted rubric dimensions.
- Requires evidence references to point to candidate turns.
- Requires evidence quotes to be literal substrings of the referenced candidate turn.
- Preserves provider/model provenance in the generated scorecard.
- Added regression tests for valid responses, fabricated quotes, unknown dimensions, missing dimensions, fenced JSON, and invalid JSON.

### Release process

- Added a canonical v0.5 release checklist to prevent re-implementing capabilities already present on `main`.
- Reconciled stale roadmap entries for Arena confidence intervals, HTML reporting, and the Nora adapter.

## 0.4.0 — 2026-09-23

### Arena

- Added provider-neutral interview-agent factory/session protocols.
- Added deterministic repeated-run Arena runner.
- Added scripted fixed-interview baseline adapter.
- Added controlled synthetic candidate scenarios.
- Added per-agent completion and turn aggregates.
- Added repeated-run question-path stability.
- Added YAML Arena configuration.
- Added `voxrubric arena` CLI command.
- Added live Nora HTTP Arena adapter.
- Added runnable Nora live Arena example.

### Reporting

- Added self-contained HTML Arena report renderer.
- Added agent overview cards.
- Added per-agent metric distribution tables.
- Added run-by-run system audit table.
- Added HTML escaping for report content.
- Added `--html-out` CLI support.
- Added HTML report generation to CI smoke coverage.

### Governance and evidence

- Added dual-lane balance metric.
- Added evidence provenance metric.
- Added candidate-rights governance audit.
- Added candidate-control recovery metric.
- Added practical tool artifact-integrity metric.
- Added literal quote provenance checks.
- Added semantic judge integrity metric.
- Added semantic judge failure audit support.
- Added transcript semantic-judge overclaim detection.

### Realtime voice

- Added realtime voice event-integrity metric.
- Added voice latency decomposition.
- Added speech-to-final p95.
- Added final-to-response p95.
- Added response-to-TTS p95.
- Added end-to-end voice p95.
- Added barge-in recovery metric.
- Added stale/malformed TTS lifecycle detection.

### Benchmarking

- Added adversarial benchmark schema and runner.
- Added known-good bilingual control trace.
- Added fabricated evidence fixture.
- Added missing-coverage fixture.
- Added broken-follow-up fixture.
- Added slow-agent fixture.
- Added fabricated semantic-judge quote fixture.
- Added deterministic synthetic candidate simulator.
- Added CI regression gates for benchmark expectations.

### Documentation

- Added Arena methodology.
- Added benchmarking methodology.
- Redesigned README as a project landing page.
- Added architecture diagrams, metric reference, roadmap, and project structure.

## 0.3.0

- Added governance-aware metrics for Nora-style traces.
- Added candidate rights and evidence-provenance validation.
- Added dual-lane standardization checks.
- Expanded default evaluator beyond core transcript metrics.

## 0.2.0

- Added adversarial benchmark execution.
- Added deterministic synthetic candidate fixtures.
- Added provider-neutral JudgeEnsemble.
- Added benchmark CLI integration.

## 0.1.0

- Initial evidence grounding, rubric coverage, follow-up integrity, latency, code-switching, and judge-agreement metrics.
- Initial CLI, trace/rubric models, tests, CI, and example fixtures.
