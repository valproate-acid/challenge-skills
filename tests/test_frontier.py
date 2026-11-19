"""Behavioral acceptance tests using real child evaluator processes."""
import importlib.util
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("frontier", ROOT / "skills/frontier-research/scripts/frontier.py")
f = importlib.util.module_from_spec(spec)
spec.loader.exec_module(f)


class HarnessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        self.source.mkdir()
        self.session = self.root / "session"
        self.manifest = self.root / "manifest.json"
        self.config = json.loads((ROOT / "examples/toy/manifest.json").read_text())
        self.config["evaluator"][0] = sys.executable
        (self.source / "candidate.json").write_text('{"x":0}')
        (self.source / "evaluate.py").write_text((ROOT / "examples/toy/evaluate.py").read_text())

    def init(self, evaluator=None):
        if evaluator:
            (self.source / "evaluate.py").write_text(evaluator)
        self.manifest.write_text(json.dumps(self.config))
        return f.initialize(self.manifest, self.source, self.session)

    def attempt(self, baseline=False, parent=None):
        return f.run(self.session, self.source, "test hypothesis", parent, baseline)

    def baseline(self):
        result = self.attempt(baseline=True)
        self.assertEqual(result["status"], "locally_validated", result)
        return result

    def test_baseline_improvement_failure_and_resume(self):
        self.init()
        base = self.baseline()
        (self.source / "candidate.json").write_text('{"x":7}')
        best = self.attempt(parent=base["id"])
        (self.source / "candidate.json").write_text('{"x":1000}')
        failure = self.attempt(parent=best["id"])
        self.assertEqual(failure["status"], "failed")
        # Reopening status from disk is the resume contract: no process state required.
        state = f.status(self.session)
        self.assertEqual(state["empirical_frontier"], [best["id"]])
        self.assertEqual(state["means_exact"][best["id"]], {"loss": "0"})
        self.assertEqual(state["evaluations_reserved"], 3)
        self.assertEqual(best["official_status"], "not_submitted")
        self.assertEqual((self.session / "attempts" / base["id"] / "candidate/candidate.json").read_text(), '{"x":0}')

    def test_requires_actual_unchanged_baseline(self):
        self.init()
        with self.assertRaises(f.ResearchError):
            self.attempt()
        (self.source / "candidate.json").write_text('{"x":7}')
        with self.assertRaises(f.ResearchError):
            self.attempt(baseline=True)

    def test_baseline_is_immutable(self):
        self.init()
        self.baseline()
        with self.assertRaises(f.ResearchError):
            self.attempt(baseline=True)

    def test_protected_source_edit_rejected_before_execution(self):
        self.init()
        (self.source / "evaluate.py").write_text("raise RuntimeError('untrusted')")
        with self.assertRaises(f.ResearchError):
            self.attempt(baseline=True)
        self.assertEqual(f.status(self.session)["evaluations_reserved"], 0)

    def test_candidate_cannot_add_protected_files(self):
        self.init()
        (self.source / "other.py").write_text("pass")
        with self.assertRaises(f.ResearchError):
            self.attempt(baseline=True)

    def test_reference_drift_blocks_resume(self):
        self.init()
        (self.session / "reference/evaluate.py").write_text("pass")
        with self.assertRaises(f.ResearchError):
            f.status(self.session)

    def test_path_traversal_and_overlap(self):
        for paths in (["../escape"], ["/tmp/x"], ["."], ["a/../b"], ["a", "a/b"], ["a", "a"], ["a\\b"]):
            with self.subTest(paths=paths):
                config = dict(self.config, editable_paths=paths)
                with self.assertRaises(f.ResearchError):
                    f.validate(config)

    def test_symlink_rejected(self):
        (self.source / "link").symlink_to(self.manifest)
        with self.assertRaises(f.ResearchError):
            self.init()

    def test_secret_and_runtime_state_excluded(self):
        (self.source / ".env").write_text("NOT_A_REAL_SECRET=fixture")
        (self.source / ".omx").mkdir()
        (self.source / ".omx/state").write_text("private")
        self.init()
        self.assertFalse((self.session / "reference/.env").exists())
        self.assertFalse((self.session / "reference/.omx").exists())

    def test_budget_reserved_including_failures(self):
        self.config["budget"]["max_evaluations"] = 1
        self.init("print('not json')")
        self.assertEqual(self.attempt(baseline=True)["status"], "failed")
        with self.assertRaises(f.ResearchError):
            self.attempt(baseline=True)
        self.assertEqual(f.status(self.session)["evaluations_reserved"], 1)

    def test_timeout_is_not_score_zero(self):
        self.config["budget"]["evaluation_seconds"] = 0.08
        self.init("import time; time.sleep(5)")
        result = self.attempt(baseline=True)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["samples"], [])
        self.assertEqual(result["error"], "timeout")

    def test_nonzero_exit_cannot_be_valid(self):
        self.init('import sys; print(\'{"valid":true,"metrics":{"loss":0}}\'); sys.exit(1)')
        self.assertEqual(self.attempt(baseline=True)["status"], "failed")

    def test_output_limit(self):
        self.init("print('x' * (5 * 1024 * 1024))")
        result = self.attempt(baseline=True)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error"], "output_limit")

    def test_finite_strict_metrics_and_valid_boolean(self):
        for output in (
            '{"valid":true,"metrics":{"loss":"NaN"}}',
            '{"valid":true,"metrics":{"loss":true}}',
            '{"valid":true,"metrics":{"loss":"Infinity"}}',
            '{"valid":1,"metrics":{"loss":0}}',
            '{"valid":true,"metrics":{"wrong":0}}',
        ):
            with self.subTest(output=output):
                path = self.root / "result.json"
                path.write_text(output)
                with self.assertRaises(f.ResearchError):
                    f.parse_result(path, self.config)

    def test_huge_integer_scores_remain_exact(self):
        self.init('print(\'{"valid":true,"metrics":{"loss":123456789012345678901234567890123456789}}\')')
        result = self.baseline()
        self.assertEqual(f.status(self.session)["means_exact"][result["id"]]["loss"], "123456789012345678901234567890123456789")

    def test_multi_seed_samples_and_exact_means(self):
        self.config["seeds"] = [0, 1, 3]
        self.init('import os,json; print(json.dumps({"valid":True,"metrics":{"loss":int(os.environ["FRONTIER_SEED"])}}))')
        base = self.baseline()
        self.assertEqual(len(base["samples"]), 3)
        self.assertEqual(f.status(self.session)["means_exact"][base["id"]]["loss"], "4/3")

    def test_completed_sample_survives_later_failure(self):
        self.config["seeds"] = [0, 1]
        self.init('import os,json; print(json.dumps({"valid":os.environ["FRONTIER_SEED"]=="0","metrics":{"loss":1}}))')
        result = self.attempt(baseline=True)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(len(result["samples"]), 1)
        self.assertEqual(f.status(self.session)["empirical_frontier"], [])
        self.assertEqual(f.status(self.session)["evaluations_reserved"], 2)

    def test_pareto_mixed_directions(self):
        self.config["objectives"] = {"loss": "min", "quality": "max"}
        self.init('import json; from pathlib import Path; x=json.loads(Path("candidate.json").read_text())["x"]; print(json.dumps({"valid":True,"metrics":{"loss":x,"quality":x}}))')
        base = self.baseline()
        (self.source / "candidate.json").write_text('{"x":7}')
        other = self.attempt(parent=base["id"])
        self.assertEqual(set(f.status(self.session)["empirical_frontier"]), {base["id"], other["id"]})

    def test_evaluator_mutation_rejected(self):
        self.init('from pathlib import Path; Path("candidate.json").write_text("{}"); print(\'{"valid":true,"metrics":{"loss":0}}\')')
        self.assertEqual(self.attempt(baseline=True)["status"], "failed")

    def test_protected_mutation_rejected(self):
        self.init('from pathlib import Path; Path("injected.txt").write_text("changed"); print(\'{"valid":true,"metrics":{"loss":0}}\')')
        self.assertEqual(self.attempt(baseline=True)["status"], "failed")

    def test_parent_must_be_validated_in_same_session(self):
        self.init()
        self.baseline()
        with self.assertRaises(f.ResearchError):
            self.attempt(parent="nonexistent")

    def test_writer_lock_and_explicit_recovery(self):
        self.init()
        with f.locked(self.session):
            with self.assertRaises(f.ResearchError):
                self.attempt(baseline=True)
        base = self.baseline()
        with closing(sqlite3.connect(self.session / "ledger.sqlite3")) as db, db:
            record = dict(base, status="running")
            db.execute("UPDATE attempts SET status='running', record=?", (json.dumps(record),))
        with self.assertRaises(f.ResearchError):
            self.attempt(baseline=True)
        self.assertEqual(f.recover(self.session)["recovered"], [base["id"]])
        state = f.status(self.session)
        self.assertEqual(state["evaluations_reserved"], 1)
        self.assertEqual(state["empirical_frontier"], [])

    def test_wall_budget_persists_across_restarts(self):
        self.init()
        with closing(sqlite3.connect(self.session / "ledger.sqlite3")) as db, db:
            meta = json.loads(db.execute("SELECT value FROM meta").fetchone()[0])
            meta["started"] -= 7200
            db.execute("UPDATE meta SET value=?", (json.dumps(meta),))
        with self.assertRaises(f.ResearchError):
            self.attempt(baseline=True)

    def test_invalid_budgets_fail_before_initialization(self):
        for budget in (0, -1, True, "10"):
            config = json.loads(json.dumps(self.config))
            config["budget"]["max_evaluations"] = budget
            with self.assertRaises(f.ResearchError):
                f.validate(config)

    def test_archive_and_evidence_integrity_on_resume(self):
        self.init()
        base = self.baseline()
        folder = self.session / "attempts" / base["id"]
        (folder / "0/stdout.txt").write_text('{"valid":true,"metrics":{"loss":0}}')
        with self.assertRaises(f.ResearchError):
            f.status(self.session)

    def test_candidate_archive_drift_on_resume(self):
        self.init()
        base = self.baseline()
        (self.session / "attempts" / base["id"] / "candidate/candidate.json").write_text('{"x":7}')
        with self.assertRaises(f.ResearchError):
            f.status(self.session)

    def test_secrets_not_inherited_by_evaluator(self):
        import os
        from unittest.mock import patch
        self.init('import os,json; print(json.dumps({"valid":"FRONTIER_TEST_SECRET" not in os.environ,"metrics":{"loss":0}}))')
        with patch.dict(os.environ, {"FRONTIER_TEST_SECRET": "test-only-value"}):
            self.baseline()


if __name__ == "__main__":
    unittest.main()
