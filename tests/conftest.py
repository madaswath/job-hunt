import os
import uuid
from pathlib import Path

import jwt
import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("AUTH_MODE", "test")
os.environ.setdefault("TEST_JWT_SECRET", "jobhunt-test-secret-32b-minimum-key!")
os.environ.setdefault("DATABASE_URL", "postgresql://jobhunt:jobhunt@127.0.0.1:5432/jobhunt")
os.environ.setdefault("UAT_SIGNOFF_SECRET", "test-signoff-secret")
os.environ.setdefault("UAT_ADMIN_USER_IDS", "uat_admin_ci")

UAT_ADMIN_USER_ID = "uat_admin_ci"


def token(user_id: str) -> str:
    return jwt.encode(
        {"sub": user_id, "email": f"{user_id}@ex.com", "name": user_id},
        os.environ["TEST_JWT_SECRET"],
        algorithm="HS256",
    )


@pytest.fixture(scope="session")
def db_ready():
    url = os.environ["DATABASE_URL"]
    try:
        import psycopg

        with psycopg.connect(url):
            pass
        import subprocess

        subprocess.run(
            ["python", str(Path(__file__).resolve().parents[1] / "scripts/apply_migrations.py")],
            check=True,
            env=os.environ.copy(),
        )
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"postgres unavailable: {exc}")
    return url


@pytest.fixture
def client(db_ready):
    from jobhunt_api.main import app

    return TestClient(app)


@pytest.fixture
def user_a():
    return f"user_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def user_b():
    return f"user_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def auth_a(user_a):
    return {"Authorization": f"Bearer {token(user_a)}"}


@pytest.fixture
def auth_b(user_b):
    return {"Authorization": f"Bearer {token(user_b)}"}


@pytest.fixture
def uat_admin_auth():
    return {
        "Authorization": f"Bearer {token(UAT_ADMIN_USER_ID)}",
        "x-uat-signoff-secret": os.environ.get("UAT_SIGNOFF_SECRET", "test-signoff-secret"),
    }


def uat_signoff_headers(admin_auth: dict) -> dict:
    return {
        **admin_auth,
        "x-uat-signoff-secret": os.environ.get("UAT_SIGNOFF_SECRET", "test-signoff-secret"),
    }
