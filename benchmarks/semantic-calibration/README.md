# Semantic Evidence Calibration Packs

These packs test whether semantic evidence judging stays conservative,
grounded, and revision-aware.

They are intentionally separate from ordinary production traces. Gold labels
live only in benchmark fixtures under `semantic_calibration_targets`.

## Packs

### `state-pack.yaml`

Covers the semantic boundary between:

- `claimed`
- `demonstrated`
- `contradicted`
- `insufficient_evidence`

It includes positive controls plus adversarial overclaim and underclaim cases.

### `freshness-pack.yaml`

Covers evidence lifecycle correctness:

- transcript corrections invalidating stale judge runs
- failed latest judge runs
- preserved inactive historical evidence
- fresh superseding evidence
- active fabricated quote rejection

## Run

```bash
voxrubric benchmark-pack benchmarks/semantic-calibration
```

Or run one suite:

```bash
voxrubric benchmark benchmarks/semantic-calibration/state-pack.yaml
voxrubric benchmark benchmarks/semantic-calibration/freshness-pack.yaml
```

A passing pack means VoxRubric correctly recognizes both the healthy controls
and the intentionally broken fixtures. It does not mean a particular model is
globally calibrated for hiring decisions.
