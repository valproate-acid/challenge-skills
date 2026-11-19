# Local controller protocol v1

`F` below is the absolute path to this skill's `scripts/frontier.py`. Commands
must run with the user's authorized compute budget. The controller itself makes
no model calls or network requests; a configured evaluator can do so and must be
reviewed before running. This is a trusted local tool, not an adversarial sandbox.

## Manifest

```json
{
  "schema_version": 1,
  "problem": "my-problem",
  "context": "source commit + verifier/toolchain/data/model/budget-policy pins",
  "editable_paths": ["submission"],
  "evaluator": ["python3", "trusted_adapter.py"],
  "objectives": {"cycles": "min", "quality": "max"},
  "seeds": [0, 1, 2],
  "budget": {
    "max_evaluations": 12,
    "wall_seconds": 3600,
    "evaluation_seconds": 120
  }
}
```

All fields shown are required; unknown top-level/budget fields are rejected.
Paths are nonoverlapping relative file/directory paths. The context identifies
the actual comparison conditions; changing any pin or seed schedule requires a
new session and baseline. The manifest, complete source snapshot and executable
bits contribute to context identity. External tools, datasets and model versions
must be pinned separately by the adapter and accurately described in `context`.
Pinning a label does not verify the remote environment.

`evaluator` is an argv array, without shell expansion. It runs in a fresh
workspace for each seed and receives `FRONTIER_SEED`. Only a minimal environment
(PATH/locale/temp path) is inherited; provider secrets, HOME and user environment
are not forwarded. Configure platform-owned credentials outside this controller.
The evaluator must return exit 0 and exactly one JSON object on stdout:

```json
{"valid": true, "metrics": {"cycles": "123456789012345678901", "quality": "0.75"}}
```

Metric names must exactly match the manifest. Use decimal strings for precise
values. Booleans, nonfinite metrics and invalid certificates are rejected.
Diagnostics belong on stderr. Logs and workspaces are retained per trial.
The evaluator must leave scored source files unchanged and write scratch
artifacts outside its working directory (e.g. a temporary directory). Adapt
verifiers that generate build products accordingly. `.git`, `.omx`, `.frontier`,
`.venv`, `__pycache__`, `.DS_Store` and `.env*` are excluded; all remaining input
files must be ordinary files, with no symlinks. Include only required source
files in the initial workspace; automatic exclusions are not a secret scanner.

## Commands

```sh
python3 "$F" init --manifest manifest.json --workspace ./source --session ./session
python3 "$F" run --session ./session --candidate ./source \
  --baseline --hypothesis "Reproduce the unmodified initialized baseline"
python3 "$F" status --session ./session
python3 "$F" run --session ./session --candidate ./candidate \
  --parent VALIDATED_ID --hypothesis "Mechanism, predicted result, rejection criterion"
```

The session and source/candidate directories must be disjoint. A candidate can
contain just the editable files or the full workspace. Protected files present
in it must match the initial snapshot exactly; missing protected files are
supplied from the reference. Missing editable files represent deletions. The
first valid run must be the unchanged baseline. A failed baseline can be retried
within budget. Once validated, the baseline cannot be relabeled or replaced.

`run` reserves the entire seed schedule before starting; failed/interrupted runs
remain charged conservatively. The wall limit runs from session initialization,
including idle time and restarts. Evaluator timeouts are bounded by the remaining
session time. Remaining time is shown by `status`; source preparation also takes
time, so the process is stopped on its deadline, not a hard real-time guarantee
for the whole CLI. stdout/stderr share a 4 MiB monitored limit; short-lived output
bursts may exceed it before termination. Children are killed as a POSIX process
group on exit/timeout; intentionally detached processes require OS isolation.

The journal records `running → locally_validated | failed | interrupted`.
Samples completed before a later failure remain recorded but a partial schedule
cannot enter the frontier. `official_status` stays `not_submitted`; this CLI
cannot certify external acceptance. Do not manually change database state.

`status` rechecks reference, validated archive and raw-log hashes and reports
all attempts, exact rational sample means and nondominated validated attempt IDs.
All comparisons are within one context. Equal scores retain both candidates.
There is no automatic overwrite/rollback of the user's worktree. Retrieve a
selected candidate from `session/attempts/ID/candidate/` into an authorized
working copy, preserving any bind-mounted directory or file roots.

## Interrupted runs

An active writer holds an exclusive local lock. A killed controller leaves a
`running` record and blocks new execution. First inspect logs and stop any orphan
evaluators in the actual OS/container, then explicitly acknowledge that action:

```sh
python3 "$F" recover --session ./session --acknowledge-stopped
python3 "$F" status --session ./session
```

Recovery marks the unfinished attempt interrupted without rerunning it, refunding
budget or erasing samples. Start a new hypothesis or repair only after inspecting
the existing evidence. A changed reference snapshot requires a new session.

Use a trusted local disk, not a shared network filesystem. Reference and ledger
are evidence-integrity checks against accidental drift, not protection from a
malicious process with access to the controller's filesystem. Copy sessions only
while idle. Keep sessions private: source and logs may contain sensitive data.
