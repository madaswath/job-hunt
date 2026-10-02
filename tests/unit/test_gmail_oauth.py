from unittest.mock import MagicMock, patch

from jobhunt_api.services import gmail_oauth


def test_oauth_configured_requires_all_fields():
    with patch("jobhunt_api.services.gmail_oauth.settings") as s:
        s.gmail_client_id = ""
        s.gmail_client_secret = "x"
        s.gmail_redirect_uri = "http://localhost/cb"
        assert not gmail_oauth.oauth_configured()


@patch("jobhunt_api.services.oauth_security.get_settings")
@patch("jobhunt_api.services.gmail_oauth.settings")
@patch("jobhunt_api.services.gmail_oauth.db")
def test_start_oauth_returns_url(db_mock, s_gmail, get_settings):
    db_mock.execute = MagicMock()
    s_gmail.gmail_client_id = "cid"
    s_gmail.gmail_client_secret = "sec"
    s_gmail.gmail_redirect_uri = "http://localhost/cb"
    s_gmail.gmail_redirect_allowlist = "http://localhost/cb"
    s_gmail.gmail_allowed_labels = "JobAlerts,Jobs"
    s_gmail.oauth_state_secret = "test-oauth-state-secret-32chars!!"
    s_gmail.test_jwt_secret = "test-oauth-state-secret-32chars!!"
    get_settings.return_value = s_gmail
    out = gmail_oauth.start_oauth("user_1", ["JobAlerts"])
    assert "auth_url" in out
    assert "state" in out
    assert "client_id=cid" in out["auth_url"]
    assert "code_challenge=" in out["auth_url"]


@patch("jobhunt_api.services.gmail_oauth.httpx.Client")
@patch("jobhunt_api.services.gmail_oauth.db")
def test_refresh_access_token(db_mock, client_cls):
    db_mock.execute = MagicMock()
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"access_token": "a", "expires_in": 3600}
    client_cls.return_value.__enter__.return_value.post.return_value = resp
    with patch("jobhunt_api.services.gmail_oauth.settings") as s:
        s.gmail_client_id = "cid"
        s.gmail_client_secret = "sec"
        tokens = gmail_oauth.refresh_access_token("refresh")
    assert tokens["access_token"] == "a"


def test_verify_revoked_no_row():
    with patch("jobhunt_api.services.gmail_oauth.db") as db_mock:
        db_mock.fetch_one.return_value = None
        assert gmail_oauth.verify_revoked("u1") is True
