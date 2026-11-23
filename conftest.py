import pytest

import main


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Each test gets its own SQLite file, so parallel worktrees/agents never share state."""
    monkeypatch.setattr(main, "DB_PATH", tmp_path / "test.db")
    main.init_db()
