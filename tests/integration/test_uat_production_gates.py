import os
from unittest.mock import patch

import pytest
from jobhunt_api import db


@pytest.fixture(autouse=True)
def uat_env(monkeypatch):
    monkeypatch.setenv("UAT_SIGNOFF_SECRET", "test-signoff-secret")
    monkeypatch.setenv("UAT_ADMIN_USER_IDS", "uat_admin_ci")
    monkeypatch.setenv("ALLOW_GMAIL_OAUTH_DEV", "true")
    monkeypatch.setenv("GMAIL_CLIENT_ID", "ci-test-client")
    monkeypatch.setenv("GMAIL_CLIENT_SECRET", "ci-test-secret")
    monkeypatch.setenv("GMAIL_REDIRECT_URI", "http://localhost:8000/api/v1/sources/gmail_alerts/oauth/callback")
    monkeypatch.setenv("GMAIL_REDIRECT_ALLOWLIST", "http://localhost:8000/api/v1/sources/gmail_alerts/oauth/callback")
    from jobhunt_api import settings as settings_mod

    settings_mod.settings = settings_mod.Settings()


def test_gmail_oauth_blocked_without_signoff(client, auth_a, monkeypatch):
    monkeypatch.setenv("ALLOW_GMAIL_OAUTH_DEV", "false")
    from jobhunt_api import settings as settings_mod

    settings_mod.settings = settings_mod.Settings()
    r = client.post("/api/v1/sources/gmail_alerts/oauth/start", headers=auth_a, json={"labels": ["JobAlerts"]})
    assert r.status_code == 403


def test_signoff_rejects_non_admin_even_with_secret(client, auth_a):
    client.get("/api/v1/me", headers=auth_a)
    r = client.post(
        "/api/v1/uat/signoff",
        headers={
            **auth_a,
            "x-uat-signoff-secret": os.environ["UAT_SIGNOFF_SECRET"],
        },
        json={"component": "gmail_alerts", "signed_by": "intruder"},
    )
    assert r.status_code == 403


def test_uat_signoff_enables_oauth_start(client, auth_a, uat_admin_auth):
    client.get("/api/v1/me", headers=uat_admin_auth)
    r = client.post(
        "/api/v1/uat/signoff",
        headers=uat_admin_auth,
        json={"component": "gmail_alerts", "signed_by": "ci", "notes": "integration"},
    )
    assert r.status_code == 200
    client.get("/api/v1/me", headers=auth_a)
    r2 = client.post("/api/v1/sources/gmail_alerts/oauth/start", headers=auth_a, json={"labels": ["JobAlerts"]})
    assert r2.status_code == 200
    assert "code_challenge=" in r2.json()["auth_url"]
    assert "gmail.readonly" in r2.json()["auth_url"]


@patch("jobhunt_api.services.gmail_oauth.httpx.Client")
def test_oauth_callback_pkce_and_revoke(client, auth_a, uat_admin_auth, mock_client_cls):
    client.get("/api/v1/me", headers=uat_admin_auth)
    client.post(
        "/api/v1/uat/signoff",
        headers=uat_admin_auth,
        json={"component": "gmail_alerts", "signed_by": "ci"},
    )
    client.get("/api/v1/me", headers=auth_a)
    start = client.post("/api/v1/sources/gmail_alerts/oauth/start", headers=auth_a, json={"labels": ["JobAlerts"]})
    state = start.json()["state"]
    resp = mock_client_cls.return_value.__enter__.return_value.post
    resp.return_value.status_code = 200
    resp.return_value.json.return_value = {"refresh_token": "rtok", "expires_in": 3600, "access_token": "atok"}
    cb = client.get(f"/api/v1/sources/gmail_alerts/oauth/callback?state={state}&code=abc")
    assert cb.status_code == 200
    revoke = client.post("/api/v1/sources/gmail_alerts/revoke", headers=auth_a)
    assert revoke.status_code == 200
    assert revoke.json()["revoke_verified"] is True


def test_signoff_invalidated_on_config_drift(client, uat_admin_auth, monkeypatch):
    client.get("/api/v1/me", headers=uat_admin_auth)
    client.post("/api/v1/uat/signoff", headers=uat_admin_auth, json={"component": "gmail_alerts", "signed_by": "ci"})
    from jobhunt_api.services import production_gates

    assert production_gates.uat_signoff_active("gmail_alerts")
    monkeypatch.setenv("TOKEN_ENCRYPTION_KEY", "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB=")
    from jobhunt_api import settings as settings_mod

    settings_mod.settings = settings_mod.Settings()
    assert not production_gates.uat_signoff_active("gmail_alerts")


def test_external_gmail_api_ingest_blocked_without_feature(client, auth_a):
    client.get("/api/v1/me", headers=auth_a)
    client.post("/api/v1/sources/gmail_alerts/connect", headers=auth_a, json={"labels": ["JobAlerts"]})
    r = client.post(
        "/api/v1/sources/gmail_alerts/ingest",
        headers=auth_a,
        json={"use_gmail_api": True},
    )
    assert r.status_code == 403


def test_deploy_readiness_reports_flags(client):
    r = client.get("/api/v1/deploy/external-gmail-readiness")
    assert r.status_code == 200
    body = r.json()
    assert body["browser_exposure_forbidden"] is True
    assert "api_feature_external_gmail" in body


def test_privacy_wipe_removes_jobs_and_user(client, auth_a, user_a):
    client.get("/api/v1/me", headers=auth_a)
    client.post("/api/v1/discovery/scans", json={"connector_id": "public_ats_fixture"}, headers=auth_a)
    assert db.fetch_one("SELECT count(*)::int AS n FROM scan_jobs WHERE user_id = %s", (user_a,))["n"] >= 1
    res = client.post("/api/v1/profile/delete", headers=auth_a, json={"confirm": True})
    assert res.status_code == 200
    assert db.fetch_one("SELECT 1 AS ok FROM app_users WHERE user_id = %s", (user_a,)) is None
    assert db.fetch_one("SELECT count(*)::int AS n FROM scan_jobs WHERE user_id = %s", (user_a,))["n"] == 0


def test_retention_purge_runs(client, auth_a):
    from jobhunt_api.services import privacy

    client.get("/api/v1/me", headers=auth_a)
    out = privacy.purge_retention_captures()
    assert "purged_captures" in out
