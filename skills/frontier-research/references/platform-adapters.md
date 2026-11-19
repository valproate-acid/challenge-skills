# Platform boundaries and adapter recipes

This release provides a local evaluator protocol, not a drop-in hosted solver.
Use each platform's current SDK/CLI and trusted evaluator. Never replace its
acceptance rules with the local frontier or a parsed claim file.

## OpenRSI

Read the assigned `OPENRSI_TASK`: workspace/candidate/read-only paths, problem
identity, model/gateway, budget and evidence mode. Smoke has no live model and
does not prove problem validity. The executable contract is
[`openrsi-exec-v1`](https://github.com/Layr-Labs/openrsi-space/blob/ddb7a6ebe90d682984f771203b26d2bb4dc32404/docs/executable-harness.md).
Build dependencies into the image; runtime downloads are unavailable. Use the
assigned model route and trusted `evaluate` service. Request-level retry signals
and remaining budget govern recovery; an unknown failure must not blindly
restart paid research. Preserve evaluations that completed before another call
failed, and retain the newest verified best.

Package only generic agent code/prompts. Retrieve problem resources from the
assigned library during the run; exclude this repository's challenge case studies
and any problem-specific candidates from the submitted image. Update mounted
candidate contents in place; renaming/swapping mount roots can fail. Local
copy-based staging does not test live bind-mount behavior. A hosted wrapper must
translate task/service results and budgets and be integration-tested separately.

## Fortress

The reference [environment adapter](https://github.com/Layr-Labs/arena-fortress/blob/eff4c39f6a08c77905cd655706a64b57d322033b/framework/harnessarena/adapter.py)
separates episode artifacts and environment scoring from the generic runner.
Retain task IDs, seeds, fort identity, suite/comparability version, gateway
accounting and per-task results. The fixed hosted model and permitted game API
are part of the contract. Infrastructure failure, harness crash and valid low
score are different outcomes.

Use the official toolkit for suite weighting, matched comparisons and confidence
bounds; a naive mean of game scores is not the official suite score. Repeated
same-seed runs remain nondeterministic. Compare contenders locally under matching
conditions and confirm selected gains on fresh games. Credit inherited leader
code and ideas. A fake evaluator tests wiring only; real game/model runs require
their own authorized environment and budget.

## Formal and cryptographic challenges

An adapter invokes the pinned official verifier in its supported environment,
then emits `valid=true` and exact metrics only after complete success. Preserve
certificate, machine-image, manifest and theorem linkage. Static policy checks,
finite comparisons, arithmetic bounds and advisory review are useful evidence,
but cannot substitute for kernel/official verification.

An adapter may keep scratch builds outside the local controller's source snapshot
and parse official score artifacts after validating process status and current
artifact identity. Record verifier/toolchain/source pins in the session context.
Refresh rule changes in a new session; do not mix scalar/product/Pareto tracks.
For a prose theorem without a deterministic verifier, keep a claim/evidence journal
and independent review; do not manufacture a numerical `valid=true` result.

## Publication and asynchronous services

Keep local candidate validity, remote receipt, remote verification and promotion
as separate records. Before an authorized upload, record payload digest and an
idempotency key if the platform supports it. Unknown response is not failure or
success: inspect existing submissions before retrying. Follow platform backoff,
quota and cancellation semantics. Local experiment recovery never retries an
external write. This release does not implement a background watcher.
