import pytest
from jobhunt_api.services.oauth_security import (
    OAuthSecurityError,
    assert_redirect_allowed,
    filter_allowed_labels,
    generate_pkce,
    sign_state,
    verify_state_signature,
)


def test_pkce_challenge():
    verifier, challenge = generate_pkce()
    assert len(verifier) > 20
    assert len(challenge) > 20


def test_state_signature_roundtrip():
    sig = sign_state("state123", "user_a", "gmail_alerts")
    verify_state_signature("state123", "user_a", "gmail_alerts", sig)
    with pytest.raises(OAuthSecurityError):
        verify_state_signature("state123", "user_b", "gmail_alerts", sig)


def test_label_allowlist(monkeypatch):
    monkeypatch.setenv("GMAIL_ALLOWED_LABELS", "JobAlerts,Jobs")
    import jobhunt_api.services.oauth_security as oauth_sec
    from jobhunt_api import settings as settings_mod

    oauth_sec.settings = settings_mod.Settings()
    assert filter_allowed_labels(["JobAlerts"]) == ["JobAlerts"]
    with pytest.raises(OAuthSecurityError):
        filter_allowed_labels(["Personal"])


def test_redirect_allowlist(monkeypatch):
    monkeypatch.setenv("GMAIL_REDIRECT_URI", "http://localhost:8000/api/v1/cb")
    monkeypatch.setenv("GMAIL_REDIRECT_ALLOWLIST", "http://localhost:8000/api/v1/cb")
    import jobhunt_api.services.oauth_security as oauth_sec
    from jobhunt_api import settings as settings_mod

    oauth_sec.settings = settings_mod.Settings()
    assert_redirect_allowed("http://localhost:8000/api/v1/cb")
    with pytest.raises(OAuthSecurityError):
        assert_redirect_allowed("http://evil.example/cb")
