# Local challenge evidence inventory

Read-only inspection, 2026-11-19. Paths below are relative to the parent challenge
workspace and identify evidence, not vendored content. Private local logs,
submission payloads and credentials are excluded from this public repository.
File SHA-256 values are recorded in `sources.json` to identify inspected bytes.

| Case | Inspected evidence | What it establishes | What it does not establish |
|---|---|---|---|
| CircuitBreaker | `circuitbreaker-research/state.md`, `reports/2026-11-05-refresh/research.md`, `reports/refined-submission-upload-blocked.json` | Historical local advisory validation, blocked upload, later source/verifier drift | Current official acceptance or a new theorem/score |
| ShorECDLP | `shor-ecdlp-research/AGENTS.md`, `PLAN.md`, `state.md` | Setup checkpoint, unmeasured upstream candidate, permitted paths and axioms | A completed baseline or verified resource score |
| Commit Golf | `commit-golf/README.md`, `benchmark.json`, `submission-pareto/README.md` | Scalar/Pareto contracts, artifact linkage requirements, locally documented candidate lineage and finite checks | Independent confirmation of the README's predecessor acceptance or current full certificate |
| Lighter Prover | Parent Git tree has `chaa/lighter-prover-challenge` gitlink `a59b7c8f216653ea133178998a32ebbf7d9130eb`; working directory absent | Historical repository reference | Source inspection, experiments or submitted results |
| Proximity Prize | Parent Git tree has `chaa/proximity-prize` gitlink `9cde12c5d2e5fee15bee0e6fa4c6d23ca9d9b1e0`; working directory absent | Historical repository reference | Source inspection, experiments or submitted results |

Observed source HEADs: CircuitBreaker `2cd3a17f3f296b7f0ac248a63a9b54a0fabdf851`,
ShorECDLP `0395f6e230b32e1856ce89d39894e44191c60f37`, Commit Golf
`0585bfb` (full SHA in source inventory). Working trees may contain ongoing changes;
HEAD alone does not identify candidate bytes. The Commit Golf local README names
an accepted predecessor but explicitly distinguishes the present candidate's checks
from full certification. We preserve that distinction.

This is the accessible local collection, not a complete account export of every
challenge submission. We did not restore absent repositories, alter sibling work,
run sibling verifiers, or query credential-gated Yukon submission history. A later
account-history collection can extend the inventory without relabeling these records.
