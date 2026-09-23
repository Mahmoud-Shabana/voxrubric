# VoxRubric

> Evidence-grounded evaluation for AI interview and voice agents.

VoxRubric is an open-source Python toolkit for testing whether an interview agent **asks the right things, follows up traceably, covers the intended rubric, supports multilingual/code-switched conversations, cites real evidence for its scores, behaves consistently across judges, and stays responsive in real time**.

It is deliberately **not** another resume-to-questions demo and it does not collapse unrelated behaviors into a single magic score.

## Why VoxRubric

Most interview-agent demos focus on generating questions and producing a final score. Production failures happen deeper in the stack:

- the agent skips a required competency;
- a follow-up is not actually grounded in the candidate's previous answer;
- a scoring model cites words the candidate never said;
- two judges produce materially different scores;
- Arabic/English code-switching appears in real conversations but is absent from the test set;
- the voice loop is accurate but too slow to feel conversational.

VoxRubric makes those failures explicit and machine-testable.

v0.4 also treats **governance behavior as testable behavior**. If an agent declares a standardized/adaptive interview policy, exposes candidate transcript corrections, or emits integrity flags, VoxRubric can validate that those guarantees remain intact in exported traces.

## Design principles

1. **Evidence before scores.** Every high-stakes score should be auditable back to transcript turns.
2. **Separate metrics.** Coverage, grounding, latency, agreement, and interaction integrity remain distinct.
3. **Provider-neutral core.** Hosted and local LLMs connect through small adapters instead of owning the architecture.
4. **Deterministic checks first.** Cheap structural failures are caught before invoking a judge model.
5. **Arabic/English is first-class.** Code-switched speech is represented in the benchmark schema rather than treated as an edge case.
6. **Human decision ownership.** The toolkit measures system behavior; it is not an autonomous hiring authority.

## What ships in v0.4

| Capability | What it measures |
|---|---|
| `evidence_grounding` | Whether cited evidence exists in the referenced transcript turn |
| `rubric_coverage` | Weighted coverage of required interview dimensions |
| `follow_up_integrity` | Whether follow-ups trace to actual candidate answers |
| `response_latency` | p50/p95/max interviewer response latency |
| `code_switching` | Arabic/Latin code-switching in candidate turns |
| `judge_agreement` | Cross-judge normalized score agreement |
| `dual_lane_balance` | Whether standardized anchors remain represented beside adaptive questions |
| `evidence_provenance` | Whether skill evidence points to real transcript turns with valid evaluator confidence |
| `governance_audit` | Candidate correction/appeal integrity and human-review-only integrity signals |

## Quick start

```bash
python -m pip install -e '.[dev]'
voxrubric eval \
  --trace examples/session.json \
  --rubric examples/python_engineer.yaml \
  --out report.md

# Run the bundled adversarial regression pack
voxrubric benchmark benchmarks/adversarial/suite.yaml

# Compare repeated controlled interview-agent runs
voxrubric arena examples/arena.yaml --out arena-result.json
```

Python API:

```python
from voxrubric.config import load_rubric, load_trace
from voxrubric import default_evaluator

trace = load_trace("examples/session.json")
rubric = load_rubric("examples/python_engineer.yaml")
report = default_evaluator(latency_budget_ms=1800).run(trace, rubric)

for metric in report.metrics:
    print(metric.metric, metric.value, metric.passed)
```

## Benchmark suites

VoxRubric can assert that known-good traces pass **and** known-bad traces fail for the expected reason.

The bundled adversarial suite covers fabricated evidence, missing competency coverage, broken follow-up lineage, excessive latency, and a bilingual grounded control. See `docs/BENCHMARKING.md`.

Synthetic candidate personas are also available for deterministic regression fixtures with configurable skill level and answer style.

## Arena

VoxRubric Arena runs the same controlled scenario and synthetic candidate profile against multiple interview-agent adapters. It keeps traces and metrics separate, measures within-agent question-path stability across repeated runs, and deliberately does not select a winner.

The included YAML example compares fixed baselines:

```bash
voxrubric arena examples/arena.yaml
```

Custom agents implement the provider-neutral `InterviewAgentFactory` / `InterviewAgentSession` protocols. See `docs/ARENA.md`.

## Trace schema

The trace is intentionally simple: ordered turns, explicit speakers, optional timing, optional rubric tags, and a parent link for adaptive follow-ups.

```json
{
  "id": "q2",
  "speaker": "interviewer",
  "text": "What evidence told you the event loop was blocked?",
  "parent_turn_id": "a1",
  "response_latency_ms": 780,
  "rubric_tags": ["concurrency", "debugging"]
}
```

A scorecard is evidence-bearing by construction:

```json
{
  "dimension": "debugging",
  "score": 8.0,
  "evidence": [
    {
      "turn_id": "a2",
      "quote": "event-loop lag with database query duration",
      "rationale": "The candidate compared competing hypotheses using measurements."
    }
  ]
}
```

## Architecture

```text
Agent / recorded interview / simulator
              |
              v
        InterviewTrace
              |
     +--------+---------+
     | deterministic   |
     | metric layer    |
     +--------+---------+
              |
     optional JudgeProvider
              |
              v
       EvaluationReport
        /      |      \
      JSON   Markdown   CI gate
```

The core package does not import a model-provider SDK. A semantic judge implements:

```python
class JudgeProvider(Protocol):
    @property
    def judge_id(self) -> str: ...
    def score(self, trace: InterviewTrace, rubric: Rubric) -> InterviewScorecard: ...
```

That boundary lets a benchmark compare providers without rewriting the evaluation system.

## Governance-aware evaluation

For Nora-style traces, the default evaluator now validates:

- standardized anchor vs adaptive question balance;
- skill evidence provenance back to real transcript turns;
- transcript revisions that preserve candidate ownership;
- appeals that reference known turns;
- integrity signals that remain explicitly human-review-only.

These metrics return N/A for generic traces that do not expose the relevant metadata, so the core remains provider- and product-neutral.

## Arabic + English example

The included example contains a natural mixed-language answer:

```text
اشتغلت على FastAPI service وكان عندنا blocking database calls
بتأخر الـ event loop...
```

VoxRubric records the fact that code-switching happened. Future benchmark packs will measure ASR preservation, semantic consistency, and follow-up robustness across Arabic dialects and Arabic/English technical speech.

## Safety and hiring use

VoxRubric should not infer or score race, religion, nationality, disability, age, gender, facial expression, attractiveness, accent prestige, or other protected/sensitive traits. Video or audio may be part of an interaction system, but hiring-relevant evaluation should remain tied to job-related rubrics and reviewable evidence.

For real hiring deployments, keep a human accountable for the decision, document the rubric, obtain appropriate consent, define retention limits, and validate the system for the jurisdiction where it is used.

## Roadmap

- [ ] `JudgeProvider` reference adapters for hosted and local models
- [x] adversarial evidence-grounding cases
- [x] deterministic synthetic candidate simulator with controllable skill profiles
- [ ] semantic follow-up quality evaluator
- [x] dual-lane standardization checks
- [x] evidence-provenance validation
- [x] candidate-rights and integrity governance audit
- [ ] ASR preservation tests for Arabic/English technical vocabulary
- [ ] interruption / barge-in / recovery benchmark
- [x] repeated-run structural path stability
- [ ] repeated-run statistical confidence intervals
- [ ] benchmark packs for software engineering, customer support, sales, and graduate hiring
- [ ] HTML report and run comparison
- [ ] public benchmark dataset with versioned schema and dataset cards

## What VoxRubric is not

It is not an ATS, not an autonomous hiring decision engine, and not a facial/emotion analysis system. It is infrastructure for making AI interview behavior measurable and auditable.

## License

Apache-2.0. See `LICENSE`.
