# Benchmarking with VoxRubric

A VoxRubric benchmark suite is a collection of interview traces plus **expected evaluator behavior**.

The goal is not to make every trace look good. A strong evaluator must fail known-bad traces for the right reason.

## Adversarial smoke suite

Run:

```bash
voxrubric benchmark benchmarks/adversarial/suite.yaml
```

The bundled suite contains five controls:

| Case | Expected behavior |
|---|---|
| grounded control | evidence, coverage, and follow-up lineage pass |
| fabricated evidence | evidence grounding fails |
| missing coverage | required rubric coverage fails |
| broken follow-up | parent-turn integrity fails |
| slow agent | p95 latency budget fails |

A suite passes when the evaluator produces the **expected pass/fail behavior for every case**.

## Suite schema

```yaml
id: my-suite
title: My interview-agent regression suite
cases:
  - id: fabricated-evidence
    description: Catch invented supporting quotes
    trace: traces/fabricated.json
    rubric: rubrics/backend.yaml
    expectations:
      - metric: evidence_grounding
        max_value: 0.0
        passed: false
```

Expectations can assert:

- `passed: true|false`
- `min_value`
- `max_value`

This allows a benchmark to test healthy behavior and deliberate failure cases without collapsing everything into one score.

## Synthetic candidates

`SyntheticCandidate` provides deterministic behavior fixtures with controlled skill level and answer style.

```python
from voxrubric.synthetic import AnswerStyle, CandidatePersona, SyntheticCandidate

persona = CandidatePersona(
    id="arabic-senior",
    skill_level=4,
    answer_style=AnswerStyle.CODE_SWITCHED,
    known_topics=["debugging"],
)

candidate = SyntheticCandidate(persona)
print(candidate.answer("How did you debug it?", "debugging"))
```

The deterministic simulator is deliberately simple: it is a regression fixture, not a claim that it reproduces human behavior. Stochastic model-backed simulators should live behind a separate adapter and should be evaluated for simulator bias before they are used to compare agents.

## Designing hard benchmark cases

Prefer cases that expose a single identifiable failure mode:

- transcript evidence that contradicts the judge's citation;
- a required competency that the agent silently skipped;
- a follow-up attached to the wrong conversation turn;
- multilingual technical speech that changes language mid-answer;
- excessive response latency despite otherwise correct content;
- repeated judge runs that materially disagree.

Avoid benchmark cases whose only difficulty is prompt length or obscure wording.
