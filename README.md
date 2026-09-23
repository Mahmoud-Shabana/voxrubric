# VoxRubric

> Evidence-grounded evaluation and benchmarking for AI interview and voice agents.

VoxRubric is an open-source Python toolkit for testing whether an interview agent **asks the right things, follows up traceably, covers the intended rubric, preserves candidate rights, uses practical tools safely, handles realtime voice interactions correctly, cites real evidence, behaves consistently across repeated runs, and stays responsive**.

It is deliberately **not** another resume-to-questions demo, and it does not collapse unrelated behaviors into one magic score.

## Why VoxRubric

Interview agents can fail far below the level of a final candidate score:

- a required competency is silently skipped;
- a follow-up is not actually linked to the candidate answer that caused it;
- a judge cites words the candidate never said;
- two judges materially disagree;
- a practical assessment leaks hidden tests or produces a score even though manual review is required;
- a candidate asks for clarification or thinking time and the agent mishandles the request;
- realtime audio sounds slow, but it is unclear whether STT, reasoning, or TTS startup is responsible;
- the agent fails to recover after the candidate interrupts it;
- repeated runs of the same controlled scenario produce unstable question paths.

VoxRubric makes those failures explicit and machine-testable.

## Design principles

1. **Evidence before scores.** High-stakes claims should be auditable back to transcript turns or practical artifacts.
2. **Separate metrics.** Coverage, grounding, latency, governance, tool integrity, voice behavior, and stability remain distinct.
3. **Provider-neutral core.** Hosted models, local models, and external interview agents connect through small adapters.
4. **Deterministic checks first.** Structural failures are caught before semantic judge calls.
5. **Arabic/English is first-class.** Code-switched speech is represented in the benchmark schema.
6. **Candidate rights are testable.** Transcript corrections, appeals, and review-only integrity signals can be validated from traces.
7. **No automatic winner.** Arena reports descriptive measurements instead of ranking interview systems.
8. **Human decision ownership.** VoxRubric measures systems; it is not an autonomous hiring authority.

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
| `evidence_provenance` | Whether skill evidence points to real transcript turns with valid provenance |
| `governance_audit` | Candidate correction/appeal integrity and human-review-only integrity signals |
| `candidate_control_recovery` | Repeat/clarify/thinking-time/resume/correction recovery behavior |
| `tool_artifact_integrity` | Tool lifecycle, artifact lineage, manual-review semantics, and hidden-data leakage |
| `voice_event_integrity` | Realtime speech/TTS lifecycle consistency |
| `voice_latency_breakdown` | STT-finalization, reasoning, TTS-startup, and end-to-end voice latency |
| `barge_in_recovery` | Whether interruptions cancel stale audio and recover through a new response |

## Quick start

```bash
python -m pip install -e '.[dev]'

voxrubric eval \
  --trace examples/session.json \
  --rubric examples/python_engineer.yaml \
  --out report.md

# Adversarial regression pack
voxrubric benchmark benchmarks/adversarial/suite.yaml \
  --out benchmark-result.json

# Repeated controlled agent comparison
voxrubric arena examples/arena.yaml \
  --out arena-result.json
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

## Adversarial benchmark suites

A VoxRubric benchmark suite can assert that known-good traces pass **and** known-bad traces fail for the expected reason.

The bundled suite covers:

- fabricated evidence;
- missing competency coverage;
- broken follow-up lineage;
- excessive latency;
- bilingual/code-switched controls.

See `docs/BENCHMARKING.md`.

## Arena

VoxRubric Arena runs the **same scenario and synthetic candidate profile** against multiple interview-agent adapters.

It preserves every trace and every metric separately, and can measure repeated-run question-path stability. It deliberately does **not** choose a winner or create a universal quality score.

```bash
voxrubric arena examples/arena.yaml
```

Current Arena support includes:

- deterministic synthetic candidates;
- repeated runs;
- scripted fixed-interview baselines;
- provider-neutral `InterviewAgentFactory` / `InterviewAgentSession` protocols;
- per-agent completion/turn aggregates;
- question-path stability;
- ordinary VoxRubric evaluation on every generated trace.

See `docs/ARENA.md`.

## Governance-aware evaluation

For Nora-style traces, VoxRubric can validate:

- standardized anchor vs adaptive question balance;
- skill-evidence provenance;
- candidate transcript corrections;
- appeals referencing real turns;
- integrity signals remaining human-review-only;
- structured candidate controls;
- practical tool lifecycle and artifact lineage;
- voice lifecycle and barge-in recovery.

Generic traces that do not expose these metadata fields remain valid; product-specific metrics return non-applicable results instead of inventing failures.

## Realtime voice evaluation

VoxRubric separates voice latency into independent components:

```text
candidate speech
      |
      v
final transcript      -> speech_to_final
      |
      v
agent response ready  -> final_to_response
      |
      v
TTS starts            -> response_to_tts
```

That makes it possible to distinguish slow STT from slow reasoning or slow speech synthesis.

The voice layer also checks event ordering and whether a barge-in actually causes stale TTS cancellation followed by a new final transcript and response.

## Tool and artifact evaluation

Interview-agent traces can include coding, case-study, whiteboard, document, and other tool artifacts.

VoxRubric validates structural invariants such as:

- submissions reference real tools;
- evaluations reference the correct submission;
- evaluated tools actually have evaluations;
- review-required artifacts are not assigned fake automatic scores;
- public payloads do not expose keys such as `hidden_tests`, `answer_key`, or `expected_solution`.

## Trace schema

The base trace remains intentionally small:

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

A semantic scorecard is evidence-bearing by construction:

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
Agent / Nora / recorded interview / simulator
                  |
                  v
            InterviewTrace
                  |
        +---------+----------+
        | deterministic      |
        | metric layer       |
        +---------+----------+
                  |
        optional JudgeProvider
                  |
                  v
           EvaluationReport
          /       |        \
       JSON    Markdown    CI

Controlled scenarios
        |
        v
      Arena
        |
        +--> Agent A repeated runs
        +--> Agent B repeated runs
        +--> baseline agents
        |
        v
descriptive comparison + stability
```

## Provider-neutral judge boundary

```python
class JudgeProvider(Protocol):
    @property
    def judge_id(self) -> str: ...

    def score(
        self,
        trace: InterviewTrace,
        rubric: Rubric,
    ) -> InterviewScorecard: ...
```

That boundary allows the same trace to be evaluated across different semantic judges without rewriting the benchmark.

## Arabic + English

The examples and synthetic fixtures support Arabic/English technical code-switching such as:

```text
اشتغلت على FastAPI service وكان عندنا blocking database calls
بتأخر الـ event loop...
```

VoxRubric currently detects code-switching structurally. More advanced ASR-preservation and semantic-consistency benchmark packs remain on the roadmap.

## Safety and hiring use

VoxRubric should not infer or score race, religion, nationality, disability, age, gender, facial expression, attractiveness, accent prestige, health, or other protected/sensitive traits.

For real hiring deployments, keep accountable human review, document job-related rubrics, obtain appropriate consent, define retention limits, and validate the system for the jurisdiction where it is used.

## Roadmap

### Implemented

- [x] adversarial evidence-grounding benchmark cases
- [x] deterministic synthetic candidate simulator
- [x] dual-lane standardization checks
- [x] evidence-provenance validation
- [x] candidate-rights and integrity governance audit
- [x] candidate-control recovery checks
- [x] practical tool/artifact integrity checks
- [x] realtime voice lifecycle checks
- [x] barge-in / interruption / recovery metric
- [x] STT / reasoning / TTS latency breakdown
- [x] repeated-run structural question-path stability
- [x] multi-agent Arena runner
- [x] YAML Arena scenarios and CLI
- [x] CI smoke execution for adversarial benchmarks and Arena

### Next

- [ ] reference semantic `JudgeProvider` adapters for hosted and local models
- [ ] semantic follow-up quality evaluator
- [ ] ASR-preservation benchmarks for Arabic/English technical vocabulary
- [ ] statistical confidence intervals across repeated stochastic runs
- [ ] richer benchmark packs for software engineering, support, sales, and graduate hiring
- [ ] HTML comparison report
- [ ] versioned public benchmark dataset and dataset cards
- [ ] external-agent adapters for remote interview systems

## What VoxRubric is not

It is not an ATS, not an autonomous hiring decision engine, not a facial/emotion analysis system, and not a leaderboard that decides which political, hiring, or human outcome is “best.”

It is infrastructure for making AI interview behavior measurable, reproducible, and auditable.

## License

Apache-2.0. See `LICENSE`.
