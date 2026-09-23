# Contributing

Thank you for improving VoxRubric.

1. Open an issue for non-trivial behavior changes.
2. Add or update tests for every metric change.
3. Keep deterministic metrics deterministic; model-based judging belongs behind `JudgeProvider` adapters.
4. Never add a metric that infers protected or sensitive traits from voice, face, name, or background.
5. Preserve metric semantics across releases. If semantics change materially, add a new metric/version instead of silently redefining an old one.

Run locally:

```bash
python -m pip install -e '.[dev]'
pytest
voxrubric eval --trace examples/session.json --rubric examples/python_engineer.yaml
```
