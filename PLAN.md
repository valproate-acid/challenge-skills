# Frontier Research implementation plan

Scope updated 2026-11-19 (Asia/Seoul): reusable skill and local harness; no sibling
challenge optimization or challenge submission is authorized by this task.

## Release acceptance

- [x] Inspect OpenRSI and Fortress primary implementation/contracts at pinned commits.
- [x] Inventory available sibling challenge records without changing them.
- [x] Compare frontier-research methods and record source-to-design reasoning.
- [x] Implement a portable skill and dependency-free local evaluation controller.
- [x] Cover baseline, invalid evidence, budgets, exact/Pareto metrics and recovery.
- [x] Complete independent behavioral forward-test and CLI end-to-end check.
- [x] Validate skill packaging and public payload; publish authorized GitHub repository.

Published repository: <https://github.com/valproate-acid/challenge-skills>.
The initial implementation passed all four GitHub CI environments:
<https://github.com/valproate-acid/challenge-skills/actions/runs/44476324454>.

## Subsequent work (not claimed by this release)

1. Select a real benchmark and authorize its compute/model budget. Implement an
   adapter against the exact active verifier. Record environment and toolchain pins.
2. Establish a real baseline; compare sequential journal, bounded multistart and
   a simple baseline at equal total cost across multiple problem instances.
3. Add platform wrappers only after testing live task schemas, mounts, evaluator
   failure handling and metered gateway budgets. Preserve official SDK behavior.
4. Validate noisy comparisons with an explicit sampling/stopping plan and held-out
   confirmation. Do not impose one confidence model across all domains.
5. Extend to async evaluators/checkpoint services only when a concrete platform
   requires it; enforce idempotent writes and uncertainty-aware recovery.

Done in the first release means a tested research workflow/tool, not proven
frontier-level scientific discovery, improved leaderboard score, or platform certification.
