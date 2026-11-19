# Challenge Skills

This repository builds reusable research skills and deterministic local tooling.
Read `skills/frontier-research/SKILL.md` and the relevant protocol before editing
the controller. Keep the skill self-contained when copied out of this repository.

- Work only in this repository unless the user explicitly expands scope. Sibling
  challenge repositories and their uncommitted changes are research inputs only.
- Preserve `.omx` hook-owned state; never commit it, local sessions or credentials.
- Keep the runtime standard-library-only and compatible with Python 3.11+ on
  macOS/Linux. No model/provider credentials or network access are needed in tests.
- Run `python3 -W error::ResourceWarning -m unittest discover -s tests -v` and
  `python3 tests/smoke_cli.py` after behavior changes.
- Never admit a score from failed/partial evaluation, mutable candidate bytes,
  mismatched context or an invalid certificate. Preserve exact numeric values.
- Keep empirical frontier, proof validity, independent review, publication and
  official acceptance distinct. Do not claim real benchmark gains from fixtures.
- Cite primary sources with immutable commits where available. Public docs contain
  original synthesis and sanitized evidence metadata, not copied private records.
- Do not add paid/provider/remote actions to local evaluation implicitly. Platform
  wrappers require separate integration tests and authorization for actual runs.
- Prefer solo execution; independent forward-testing is useful for substantial
  skill behavior changes. Follow the user's permitted model/effort policy.
