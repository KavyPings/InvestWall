"""Pytest fixtures — isolated SQLite DB + FastAPI test client."""
from __future__ import annotations

import os
import tempfile

import pytest

# Force offline, deterministic config before app imports. Heavy ML models are
# disabled for unit tests (they're covered by dedicated integration checks);
# the suite exercises the rule/heuristic logic and must stay fast + offline.
os.environ.setdefault("ENABLE_DNS", "0")
os.environ.setdefault("LLM_PROVIDER", "template")
os.environ.setdefault("ENABLE_TRANSFORMERS", "0")
os.environ.setdefault("ENABLE_WHISPER", "0")
os.environ.setdefault("ENABLE_IMAGE_MODEL", "0")

_db_fd, _db_path = tempfile.mkstemp(suffix=".db")
os.close(_db_fd)
os.environ["DATABASE_URL"] = f"sqlite:///{_db_path}"


@pytest.fixture(scope="session")
def client():
    from fastapi.testclient import TestClient

    from app.db.base import init_db
    from app.main import app

    init_db()
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session", autouse=True)
def _cleanup():
    yield
    try:
        os.remove(_db_path)
    except OSError:
        pass
