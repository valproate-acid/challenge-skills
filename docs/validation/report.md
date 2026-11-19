# Validation: v0.1.0

Date: 2026-11-19 (Asia/Seoul). Local host: macOS arm64. These checks establish
local workflow behavior, not frontier scientific capability or benchmark gains.

| Check | Observed result | Evidence |
|---|---|---|
| Python 3.15.2 behavioral tests | 27 passed; resource warnings treated as errors | [unit-python315.txt](unit-python315.txt) |
| Python 3.12.13 behavioral tests | 27 passed; resource warnings treated as errors | [unit-python312.txt](unit-python312.txt) |
| CLI subprocess workflow, paths containing spaces | Baseline loss 49 → candidate loss 0; invalid candidate rejected; 3 evaluations reserved | [cli-smoke.json](cli-smoke.json), `tests/smoke_cli.py` |
| Official skill-creator validator | `Skill is valid!` | Temporary uv/PyYAML environment; runtime remains stdlib-only |
| Independent skill forward-test | Baseline and nondominated tradeoff retained; invalid candidate excluded; resumable journal created | [forward-test.json](forward-test.json) |

Behavioral tests exercise immutable baseline, protected-source drift, symlinks and
path traversal, invalid certificates, nonzero exit, timeout, output limit, exact
large numbers, mixed objective directions, multi-seed means, partial failure,
conservative budget reservation, wall deadline after restart, exclusive writer
lock, explicit interrupted recovery, archive/log drift and secret environment
exclusion. They run actual evaluator subprocesses, without model/network calls.

The independent evaluator used a toy sorting task with correctness checks and
declared resource proxies. The proxy values are not measured latency or memory.
The test confirms operational use of the skill and identifies that limit; it does
not prove simultaneous improvement. Feedback clarified that offline fixtures do
not require irrelevant web retrieval. A changed evaluator requires a new context
and baseline, as recorded in the checkpoint.

To reproduce the official packaging validation when the host lacks PyYAML:

```sh
uv run --with pyyaml python /path/to/skill-creator/scripts/quick_validate.py \
  skills/frontier-research
```

Only the validator needs PyYAML. It is not a runtime requirement. GitHub CI is
configured for Python 3.11/3.13 on Ubuntu/macOS; its actual run outcome is separate
from the local results above.

Not run: real OpenRSI/Dungeness, Fortress game/model, sibling Lean/verifier builds,
paid-model experiments, hosted task/mount integration, statistical efficacy study,
or official challenge submission. Source fingerprints identify inspection bytes,
not independent correctness verification of inherited research claims.
