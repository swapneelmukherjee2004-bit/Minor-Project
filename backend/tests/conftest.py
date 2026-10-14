"""Test environment: real PostgreSQL test database, real Chromium, loopback fixture server.
Env vars are set BEFORE the app is imported."""
import os
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL", "postgresql+psycopg://auditor:auditor@localhost:5432/auditor_test")
os.environ["STORAGE_DIR"] = tempfile.mkdtemp(prefix="aa-shots-")
os.environ["DATASET_DIR"] = str(REPO / "dataset")
os.environ["AI_PROVIDER"] = "mock"
os.environ["RATE_LIMIT_AUDITS"] = "1000/minute"
os.environ["RATE_LIMIT_DEFAULT"] = "10000/minute"

import pytest  # noqa: E402

from app.services.evaluation_service import serve_fixtures  # noqa: E402

FIX_ORIGIN, _srv = serve_fixtures(REPO / "dataset")
os.environ["LOCAL_FIXTURE_ORIGINS"] = FIX_ORIGIN

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.db.base import Base  # noqa: E402
from app.db.session import get_engine  # noqa: E402


@pytest.fixture(scope="session")
def fix_origin() -> str:
    return FIX_ORIGIN


@pytest.fixture(scope="session", autouse=True)
def _schema():
    import app.models  # noqa: F401
    eng = get_engine()
    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    yield


@pytest.fixture()
def client():
    from app.main import create_app
    with get_engine().begin() as c:
        c.execute(text("TRUNCATE audits, findings, eval_datasets, eval_cases, ground_truth, eval_runs, eval_results CASCADE"))
    with TestClient(create_app()) as c:
        yield c
