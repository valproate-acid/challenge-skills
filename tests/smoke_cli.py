#!/usr/bin/env python3
"""Exercise the public CLI end-to-end from a working directory with spaces."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "skills/frontier-research/scripts/frontier.py"


def main():
    with tempfile.TemporaryDirectory(prefix="frontier CLI ") as directory:
        root = Path(directory)
        source = root / "source tree"
        session = root / "session state"
        shutil.copytree(ROOT / "examples/toy", source, ignore=shutil.ignore_patterns("__pycache__"))
        config = json.loads((source / "manifest.json").read_text())
        config["evaluator"][0] = sys.executable
        (source / "manifest.json").write_text(json.dumps(config))

        def call(*args, expected=0):
            process = subprocess.run([sys.executable, str(CLI), *map(str, args)],
                                     cwd=root, capture_output=True, text=True, timeout=15)
            if process.returncode != expected:
                raise AssertionError((process.returncode, process.stdout, process.stderr))
            return json.loads(process.stdout if process.stdout else process.stderr)

        call("init", "--manifest", source / "manifest.json", "--workspace", source, "--session", session)
        baseline = call("run", "--session", session, "--candidate", source,
                        "--baseline", "--hypothesis", "Unmodified baseline")
        (source / "candidate.json").write_text('{"x":7}')
        best = call("run", "--session", session, "--candidate", source,
                    "--parent", baseline["id"], "--hypothesis", "x=7 eliminates squared error")
        (source / "candidate.json").write_text('{"x":1000}')
        failed = call("run", "--session", session, "--candidate", source,
                      "--hypothesis", "Out-of-contract candidate must be rejected", expected=1)
        state = call("status", "--session", session)
        assert state["means_exact"][baseline["id"]]["loss"] == "49", state
        assert state["means_exact"][best["id"]]["loss"] == "0", state
        assert state["empirical_frontier"] == [best["id"]], state
        assert state["evaluations_reserved"] == 3, state
        assert failed["status"] == "failed" and failed["samples"] == [], failed
        assert all(r["official_status"] == "not_submitted" for r in state["attempts"]), state
        assert call("recover", "--session", session, "--acknowledge-stopped")["recovered"] == []
        print(json.dumps({"status": "PASS", "baseline_loss": "49", "candidate_loss": "0",
                          "invalid_candidate": "failed", "evaluations_reserved": 3,
                          "source_unchanged_by_controller": True, "network_or_model_calls": 0}))


if __name__ == "__main__":
    main()
