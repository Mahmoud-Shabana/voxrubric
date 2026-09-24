# ASR Preservation Benchmark Pack

This pack evaluates transcript preservation for Arabic/English technical interview speech.

It is deliberately deterministic. Each candidate turn may include:

- `asr_reference_text`: a manual/reference transcript used only for benchmark evaluation;
- `asr_critical_terms`: job-relevant technical terms that should survive transcription.

The `asr_preservation` metric reports:

- mean word error rate (WER);
- mean word accuracy;
- critical-term recall;
- Arabic/Latin code-switch preservation;
- per-turn provenance for the comparison.

The benchmark includes both healthy controls and intentionally broken ASR outputs. A passing pack means VoxRubric recognizes those expected behaviors; it is not a general claim about any ASR provider or dialect population.

Run:

```bash
voxrubric benchmark-pack benchmarks/asr-preservation
```
