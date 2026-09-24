# Role / Domain Benchmark Packs

These packs verify that VoxRubric's deterministic evaluation behavior generalizes across distinct interview domains rather than only Python/backend fixtures.

Included domains:

- Customer Support — Arabic/English code-switching, discovery, de-escalation, documentation.
- Data Analyst — SQL, experiment design, analytical communication, follow-up lineage.
- Site Reliability Engineering — incident response, observability, reliability.

Each pack contains a healthy control and an intentional failure case. The expected failures are part of the regression contract.

Run all domain packs:

```bash
voxrubric benchmark-pack benchmarks/role-domains
```

These are evaluator regression fixtures, not claims that the included questions are a complete hiring rubric for any role.
