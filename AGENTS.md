# AGENTS.md — Recipe Box

- App: `main.py` (FastAPI + SQLite). Tests: `test_main.py` plus one `test_<feature>.py` per feature.
- Run tests: `$VENV/bin/pytest -q`. Every test runs against its own temp DB (`conftest.py`).
- **Parallel-work rules:** stay inside your own git worktree. Put new tests in a **new file**
  `test_<feature>.py`, not in `test_main.py`, so that parallel branches don't conflict. Add new routes
  at the end of `main.py`. Never edit `conftest.py`, `AGENTS.md`, or another task's files.
- Never commit, push, merge, or touch other worktrees. The human integrates.
