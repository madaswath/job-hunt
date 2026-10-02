from jobhunt_api.redact import redact, sanitize_for_alert


def test_redact_oauth_code():
    assert "[REDACTED]" in redact("callback?code=4/0abc123&state=xyz")


def test_sanitize_alert_strips_body():
    safe = sanitize_for_alert({"user_id": "u1", "body": "secret email body", "error": "refresh_token=abc"})
    assert safe["body"] == "[REDACTED]"
    assert "abc" not in str(safe["error"])
