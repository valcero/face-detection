import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.db import get_db_session
from app.main import app


class DummySession:

    def __init__(self):
        self.added = []

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        return None

    async def refresh(self, obj):
        # Ensure the object has an id if code ever reaches this point.
        if getattr(obj, "id", None) is None:
            obj.id = uuid.uuid4()


@pytest.fixture()
def client():
    async def _override():
        yield DummySession()

    app.dependency_overrides[get_db_session] = _override
    return TestClient(app)


def test_upload_rejects_bad_extension(client, monkeypatch, tmp_path: Path):
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))

    # Unsupported extension should fail before any DB interaction.
    files = {"file": ("bad.txt", b"not a video", "text/plain")}
    res = client.post("/api/videos", files=files)
    assert res.status_code == 415

