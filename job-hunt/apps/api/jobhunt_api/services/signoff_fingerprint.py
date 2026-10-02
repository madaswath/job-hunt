import hashlib
import json

from jobhunt_connectors.config import gmail_allowed_labels
from jobhunt_connectors.gmail_alerts import GMAIL_CONNECTOR_VERSION, GMAIL_OAUTH_SCOPES

from jobhunt_api.settings import settings


def gmail_config_fingerprint() -> str:
    material = {
        "connector_version": GMAIL_CONNECTOR_VERSION,
        "oauth_scopes": sorted(GMAIL_OAUTH_SCOPES),
        "gmail_allowed_labels": sorted(gmail_allowed_labels()),
        "encryption_key_fingerprint": hashlib.sha256(settings.token_encryption_key.encode()).hexdigest()[:16],
        "policy_retention_days": 90,
    }
    blob = json.dumps(material, sort_keys=True).encode()
    return hashlib.sha256(blob).hexdigest()
