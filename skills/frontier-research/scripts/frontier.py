#!/usr/bin/env python3
"""Bounded local evaluation ledger. Python 3.11+, standard library only.

Runs trusted evaluators, not a security sandbox. An agent uses this CLI between
hypothesis/proposal steps; it never starts paid models or remote submissions.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from decimal import Decimal, InvalidOperation
import hashlib
import json
import math
import os
import platform
from pathlib import Path, PurePosixPath
import shutil
import signal
import sqlite3
import subprocess
import sys
import time
import uuid


class ResearchError(ValueError):
    pass


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def relative(value):
    if not isinstance(value, str) or not value or "\\" in value:
        raise ResearchError("paths must be nonempty POSIX relative paths")
    p = PurePosixPath(value)
    if p.is_absolute() or any(x in ("", ".", "..") for x in value.split("/")):
        raise ResearchError(f"unsafe relative path: {value}")
    return value


def number(value):
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        raise ResearchError("metric must be a finite decimal number or decimal string")
    try:
        result = Decimal(str(value))
    except InvalidOperation as exc:
        raise ResearchError("invalid decimal metric") from exc
    if not result.is_finite():
        raise ResearchError("metric must be finite")
    return result


def positive(value):
    return type(value) in (int, float) and math.isfinite(value) and value > 0


def validate(config):
    required = {"schema_version", "problem", "context", "editable_paths", "evaluator", "objectives", "budget", "seeds"}
    if not isinstance(config, dict) or set(config) != required or config["schema_version"] != 1:
        raise ResearchError("manifest must contain exactly the schema-v1 fields; see protocol.md")
    for field in ("problem", "context"):
        if not isinstance(config[field], str) or not config[field].strip():
            raise ResearchError(f"{field} must be a nonempty identity/version string")
    paths = config["editable_paths"]
    if not isinstance(paths, list) or not paths:
        raise ResearchError("editable_paths must be nonempty")
    for p in paths:
        relative(p)
    for i, a in enumerate(paths):
        if any(a == b or a.startswith(b + "/") or b.startswith(a + "/") for b in paths[i + 1:]):
            raise ResearchError("editable paths must not overlap")
    argv = config["evaluator"]
    if not isinstance(argv, list) or not argv or any(not isinstance(x, str) or not x or "\0" in x for x in argv):
        raise ResearchError("evaluator must be a nonempty argv list")
    objectives = config["objectives"]
    if not isinstance(objectives, dict) or not objectives or any(not isinstance(k, str) or not k or v not in ("min", "max") for k, v in objectives.items()):
        raise ResearchError("objectives must map metric names to min/max")
    budget = config["budget"]
    if not isinstance(budget, dict) or set(budget) != {"max_evaluations", "wall_seconds", "evaluation_seconds"}:
        raise ResearchError("invalid budget fields")
    if type(budget["max_evaluations"]) is not int or budget["max_evaluations"] < 1:
        raise ResearchError("max_evaluations must be a positive integer")
    if not all(positive(budget[k]) for k in ("wall_seconds", "evaluation_seconds")):
        raise ResearchError("time budgets must be finite and positive")
    seeds = config["seeds"]
    if not isinstance(seeds, list) or not seeds or any(type(x) is not int for x in seeds) or len(set(seeds)) != len(seeds):
        raise ResearchError("seeds must be distinct integers")
    if len(seeds) > budget["max_evaluations"]:
        raise ResearchError("budget cannot cover one complete seed schedule")
    return config


EXCLUDED = {".git", ".omx", ".frontier", ".venv", "__pycache__", ".DS_Store"}


def inventory(root):
    """Hash regular source files, rejecting symlinks/special files; exclude private state."""
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ResearchError("workspace must be an ordinary directory")
    out = {}
    for folder, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = sorted(x for x in dirs if x not in EXCLUDED and not x.startswith(".env"))
        for name in dirs + sorted(files):
            if name in EXCLUDED or name.startswith(".env"):
                continue
            path = Path(folder) / name
            if path.is_symlink():
                raise ResearchError(f"symlink not allowed: {path.relative_to(root)}")
            if path.is_dir():
                continue
            if not path.is_file():
                raise ResearchError("special files are not supported")
            out[path.relative_to(root).as_posix()] = {
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "executable": bool(path.stat().st_mode & 0o111),
            }
    return out


def copy_files(source, target, files):
    for name in files:
        src, dst = Path(source) / name, Path(target) / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def editable(name, config):
    return any(name == p or name.startswith(p + "/") for p in config["editable_paths"])


@contextmanager
def connect(session):
    if not (session / "ledger.sqlite3").is_file():
        raise ResearchError("not an initialized session")
    db = sqlite3.connect(session / "ledger.sqlite3")
    db.row_factory = sqlite3.Row
    try:
        with db:
            yield db
    finally:
        db.close()


@contextmanager
def locked(session):
    # flock is deliberately scoped to macOS/Linux, matching our subprocess-group cleanup.
    import fcntl
    if not (session / "ledger.sqlite3").is_file():
        raise ResearchError("not an initialized session")
    with (session / "session.lock").open("a") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ResearchError("session already has an active writer") from exc
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def read_meta(db):
    return json.loads(db.execute("SELECT value FROM meta").fetchone()[0])


def verified_meta(session, db):
    meta = read_meta(db)
    if digest(meta["config"]) != meta["config_hash"]:
        raise ResearchError("stored manifest fingerprint changed")
    if inventory(session / "reference") != meta["reference_files"]:
        raise ResearchError("reference snapshot changed; start a new session")
    return meta


def initialize(manifest, workspace, session):
    config = validate(read_json(manifest))
    source, session = Path(workspace).resolve(), Path(session).resolve()
    if session == source or source in session.parents or session in source.parents:
        raise ResearchError("session and workspace must be disjoint directories")
    files = inventory(source)
    if not any(editable(x, config) for x in files):
        raise ResearchError("no editable source files found")
    session.mkdir(parents=True, exist_ok=False)
    (session / "reference").mkdir()
    copy_files(source, session / "reference", files)
    if inventory(session / "reference") != files:
        raise ResearchError("source changed during initialization")
    meta = {"config": config, "config_hash": digest(config), "reference_files": files,
            "reference_hash": digest(files), "started": time.time()}
    from contextlib import closing
    with closing(sqlite3.connect(session / "ledger.sqlite3")) as db, db:
        db.execute("CREATE TABLE meta (value TEXT NOT NULL)")
        db.execute("INSERT INTO meta VALUES (?)", (canonical(meta),))
        db.execute("""CREATE TABLE attempts (
            id TEXT PRIMARY KEY, created REAL, hypothesis TEXT, parent TEXT,
            baseline INTEGER, evaluations INTEGER, status TEXT, record TEXT)""")
    return {"session": str(session), "context_hash": digest([config, files]), "status": "initialized"}


def execute(argv, cwd, stdout, stderr, seconds, seed):
    env = {k: os.environ[k] for k in ("PATH", "LANG", "LC_ALL", "TMPDIR", "SYSTEMROOT") if k in os.environ}
    env.update(FRONTIER_SEED=str(seed), PYTHONHASHSEED=str(seed % (2**32)), PYTHONDONTWRITEBYTECODE="1")
    with stdout.open("wb") as out, stderr.open("wb") as err:
        proc = subprocess.Popen(argv, cwd=cwd, env=env, stdout=out, stderr=err, start_new_session=True)
        reason = None
        try:
            deadline = time.monotonic() + seconds
            while proc.poll() is None:
                if time.monotonic() >= deadline:
                    reason = "timeout"
                    break
                if stdout.stat().st_size + stderr.stat().st_size > 4 * 1024 * 1024:
                    reason = "output_limit"
                    break
                time.sleep(0.02)
        finally:
            # Kill descendants even if the direct evaluator has already exited.
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            proc.wait()
        if reason:
            raise ResearchError(reason)
        if stdout.stat().st_size + stderr.stat().st_size > 4 * 1024 * 1024:
            raise ResearchError("output_limit")
        if proc.returncode != 0:
            raise ResearchError(f"evaluator exit {proc.returncode}")


def parse_result(path, config):
    result = json.loads(path.read_text(), parse_float=Decimal)
    if not isinstance(result, dict) or result.get("valid") is not True:
        raise ResearchError("evaluator did not certify valid=true")
    metrics = result.get("metrics")
    if not isinstance(metrics, dict) or set(metrics) != set(config["objectives"]):
        raise ResearchError("evaluator metrics must exactly match objectives")
    return {k: str(number(v)) for k, v in metrics.items()}


def run(session, candidate, hypothesis, parent=None, baseline=False):
    session, candidate = Path(session).resolve(), Path(candidate).resolve()
    if not hypothesis.strip():
        raise ResearchError("hypothesis must be nonempty")
    if session == candidate or session in candidate.parents or candidate in session.parents:
        raise ResearchError("candidate and session must be disjoint")
    with locked(session), connect(session) as db:
        meta = verified_meta(session, db)
        config = meta["config"]
        previous = list(db.execute("SELECT * FROM attempts"))
        if any(x["status"] == "running" for x in previous):
            raise ResearchError("interrupted attempt requires explicit recover before continuing")
        if parent and not any(x["id"] == parent and x["status"] == "locally_validated" for x in previous):
            raise ResearchError("parent must be a locally validated attempt in this session")
        has_baseline = any(x["baseline"] and x["status"] == "locally_validated" for x in previous)
        if baseline == has_baseline:
            raise ResearchError("establish one valid --baseline before candidates; baseline is immutable")
        if baseline and parent:
            raise ResearchError("baseline cannot have a parent")
        files = inventory(candidate)
        protected = {k: v for k, v in meta["reference_files"].items() if not editable(k, config)}
        for name, value in files.items():
            if not editable(name, config) and protected.get(name) != value:
                raise ResearchError(f"candidate changes protected file: {name}")
        if baseline and {k: v for k, v in files.items() if editable(k, config)} != {
                k: v for k, v in meta["reference_files"].items() if editable(k, config)}:
            raise ResearchError("baseline must match the initialized editable snapshot")
        count = len(config["seeds"])
        if sum(x["evaluations"] for x in previous) + count > config["budget"]["max_evaluations"]:
            raise ResearchError("evaluation budget exhausted")
        if time.time() - meta["started"] >= config["budget"]["wall_seconds"]:
            raise ResearchError("wall budget exhausted")
        identity = uuid.uuid4().hex
        folder = session / "attempts" / identity
        folder.mkdir(parents=True)
        # Candidate-only archive; evaluators run in disposable copies of the reference.
        archive = folder / "candidate"
        archive.mkdir()
        selected = {k: v for k, v in files.items() if editable(k, config)}
        copy_files(candidate, archive, selected)
        if inventory(archive) != selected:
            raise ResearchError("candidate changed during snapshot")
        record = {"id": identity, "hypothesis": hypothesis, "parent": parent,
                  "baseline": baseline, "candidate_hash": digest(selected),
                  "context_hash": digest([config, meta["reference_files"]]),
                  "controller_environment": {"python": platform.python_version(),
                                             "platform": platform.platform(), "argv": config["evaluator"]},
                  "samples": [], "status": "running", "official_status": "not_submitted"}
        db.execute("INSERT INTO attempts VALUES (?,?,?,?,?,?,?,?)", (
            identity, time.time(), hypothesis, parent, baseline, count, "running", canonical(record)))
        db.commit()  # Reserve the complete schedule before starting any process.
        started = time.monotonic()
        try:
            for index, seed in enumerate(config["seeds"]):
                seconds = min(config["budget"]["evaluation_seconds"],
                              config["budget"]["wall_seconds"] - (time.time() - meta["started"]))
                if seconds <= 0:
                    raise ResearchError("wall budget exhausted")
                trial = folder / str(index)
                work = trial / "workspace"
                work.mkdir(parents=True)
                copy_files(session / "reference", work, protected)
                copy_files(archive, work, selected)
                stdout, stderr = trial / "stdout.txt", trial / "stderr.txt"
                execute(config["evaluator"], work, stdout, stderr, seconds, seed)
                after = inventory(work)
                if {k: v for k, v in after.items() if not editable(k, config)} != protected:
                    raise ResearchError("evaluator changed protected files; no score admitted")
                if {k: v for k, v in after.items() if editable(k, config)} != selected:
                    raise ResearchError("candidate mutated during evaluation; no score admitted")
                record["samples"].append({"seed": seed, "metrics": parse_result(stdout, config),
                    "stdout_sha256": hashlib.sha256(stdout.read_bytes()).hexdigest(),
                    "stderr_sha256": hashlib.sha256(stderr.read_bytes()).hexdigest()})
                # Persist completed evaluations even if a later sample or the controller fails.
                db.execute("UPDATE attempts SET record=? WHERE id=?", (canonical(record), identity))
                db.commit()
            verified_meta(session, db)
            record["status"] = "locally_validated"
        except (Exception, KeyboardInterrupt) as exc:
            record["status"] = "failed" if not isinstance(exc, KeyboardInterrupt) else "interrupted"
            record["error"] = str(exc) or "interrupted"
        record["elapsed_seconds"] = time.monotonic() - started
        db.execute("UPDATE attempts SET status=?, record=? WHERE id=?", (
            record["status"], canonical(record), identity))
        db.commit()
        return record


def mean_metrics(record):
    # Exact rational averaging avoids Decimal context rounding for huge integers.
    from fractions import Fraction
    names = record["samples"][0]["metrics"]
    return {k: sum(Fraction(s["metrics"][k]) for s in record["samples"]) / len(record["samples"]) for k in names}


def dominates(a, b, objectives):
    return all(a[k] <= b[k] if d == "min" else a[k] >= b[k] for k, d in objectives.items()) and any(
        a[k] < b[k] if d == "min" else a[k] > b[k] for k, d in objectives.items())


def status(session):
    session = Path(session).resolve()
    with connect(session) as db:
        meta = verified_meta(session, db)
        rows = list(db.execute("SELECT * FROM attempts ORDER BY created, id"))
    valid = [json.loads(x["record"]) for x in rows if x["status"] == "locally_validated"]
    for record in valid:
        folder = session / "attempts" / record["id"]
        if digest(inventory(folder / "candidate")) != record["candidate_hash"]:
            raise ResearchError("validated candidate archive changed")
        for index, sample in enumerate(record["samples"]):
            for name in ("stdout", "stderr"):
                if hashlib.sha256((folder / str(index) / f"{name}.txt").read_bytes()).hexdigest() != sample[f"{name}_sha256"]:
                    raise ResearchError("validated evaluator evidence changed")
    scores = {r["id"]: mean_metrics(r) for r in valid}
    frontier = [r["id"] for r in valid if not any(dominates(scores[s["id"]], scores[r["id"]], meta["config"]["objectives"]) for s in valid)]
    return {"problem": meta["config"]["problem"], "context": meta["config"]["context"],
            "evaluations_reserved": sum(r["evaluations"] for r in rows),
            "evaluation_budget": meta["config"]["budget"]["max_evaluations"],
            "wall_seconds_remaining": max(0, meta["config"]["budget"]["wall_seconds"] - (time.time() - meta["started"])),
            "attempts": [json.loads(r["record"]) for r in rows],
            "empirical_frontier": frontier,
            "means_exact": {k: {n: str(v) for n, v in values.items()} for k, values in scores.items()},
            "interpretation": "Local evaluator results only. Empirical means are not confidence bounds or official acceptance."}


def recover(session):
    session = Path(session).resolve()
    with locked(session), connect(session) as db:
        verified_meta(session, db)
        identities = []
        for row in db.execute("SELECT * FROM attempts WHERE status='running'").fetchall():
            record = json.loads(row["record"])
            record.update(status="interrupted", error="explicit recovery; reserved evaluations remain charged")
            db.execute("UPDATE attempts SET status=?, record=? WHERE id=?", ("interrupted", canonical(record), row["id"]))
            identities.append(row["id"])
        db.commit()
    return {"recovered": identities, "rerun": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init")
    init.add_argument("--manifest", type=Path, required=True)
    init.add_argument("--workspace", type=Path, required=True)
    init.add_argument("--session", type=Path, required=True)
    attempt = sub.add_parser("run")
    attempt.add_argument("--session", type=Path, required=True)
    attempt.add_argument("--candidate", type=Path, required=True)
    attempt.add_argument("--hypothesis", required=True)
    attempt.add_argument("--parent")
    attempt.add_argument("--baseline", action="store_true")
    for name in ("status", "recover"):
        p = sub.add_parser(name)
        p.add_argument("--session", type=Path, required=True)
        if name == "recover":
            p.add_argument("--acknowledge-stopped", action="store_true", required=True,
                           help="confirm orphan evaluator processes have been stopped")
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            result = initialize(args.manifest, args.workspace, args.session)
        elif args.command == "run":
            result = run(args.session, args.candidate, args.hypothesis, args.parent, args.baseline)
        elif args.command == "status":
            result = status(args.session)
        else:
            result = recover(args.session)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if result.get("status") in ("failed", "interrupted") else 0
    except (ResearchError, OSError, ValueError, sqlite3.Error) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
