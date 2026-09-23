# VoxRubric Arena

Arena runs the **same scenario and synthetic candidate profile** against multiple interview-agent adapters and keeps their outputs separate.

It is designed for descriptive comparison and regression research. Arena does **not** declare a winner, rank agents, or collapse unlike metrics into a single score.

## Why Arena exists

Interview agents can differ in ways that a final candidate score hides:

- one agent may cover all required competencies while another repeatedly probes one topic;
- one may use more follow-ups;
- one may require more candidate turns;
- one may change its question path materially between identical repeated runs;
- one may have lower latency but weaker coverage;
- one may behave differently on Arabic/English code-switching.

Arena preserves those dimensions rather than deciding how they should be weighted.

## Run the included baseline scenario

```bash
voxrubric arena examples/arena.yaml --out arena-result.json
```

The example defines:

- one rubric;
- one synthetic candidate persona;
- repeated runs;
- two fixed scripted baseline agents.

The output contains every generated trace, every VoxRubric evaluation report, and per-agent aggregates.

## Adapter contract

An agent under test implements two small interfaces:

```python
class InterviewAgentSession(Protocol):
    async def start(self, *, role, rubric, locale) -> AgentUtterance: ...
    async def respond(self, candidate_text: str) -> AgentUtterance: ...

class InterviewAgentFactory(Protocol):
    @property
    def agent_id(self) -> str: ...
    def create(self) -> InterviewAgentSession: ...
```

The factory requirement is deliberate: every repetition receives a clean agent session so state cannot leak between runs.

## Synthetic candidate control

Arena currently uses the deterministic `SyntheticCandidate` fixture.

The candidate profile can control:

- skill level;
- terse/concrete/rambling/code-switched answer style;
- known topics;
- weak topics.

Determinism is useful for regression testing because the agent sees the same controlled behavior on every run.

A future stochastic simulator should be treated as another model under evaluation, not as ground truth.

## Repeated-run stability

For two or more runs of one agent, Arena computes **question-path stability**.

At each interviewer step it compares the rubric-tag sets using Jaccard similarity, then averages over the aligned path. Missing extra steps reduce similarity.

This is intentionally structural. It does not claim semantically different wording is necessarily bad.

## Metrics

Each run is evaluated with the ordinary VoxRubric evaluator, so the Arena result can include:

- rubric coverage;
- follow-up integrity;
- latency;
- code switching;
- evidence grounding when scorecards exist;
- dual-lane balance when declared;
- governance checks when exported;
- candidate-control recovery;
- tool-artifact integrity.

Aggregates retain each metric independently with mean/min/max.

## What Arena does not do

Arena does not:

- choose the best hiring system;
- assign a universal quality score;
- claim a synthetic candidate represents real applicants;
- infer protected or sensitive traits;
- convert stability into correctness.

Its purpose is to make agent behavior observable under controlled repeated scenarios.
