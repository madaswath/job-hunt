from jobhunt_connectors.catalog import get_connector

FORBIDDEN_GLOBAL = {"submit_application", "send_email", "send_linkedin", "scrape_authenticated"}
INGESTABLE_CONNECTOR_STATUSES = frozenset({"live", "ingestion_ready"})


def is_external_action_allowed(action: str, *, approved: bool, audit_recorded: bool) -> bool:
    if action in FORBIDDEN_GLOBAL:
        return False
    if action in {"open_apply_url", "create_email_draft"}:
        return approved and audit_recorded
    return True


def assert_connector_operation(connector_id: str, operation: str) -> None:
    connector = get_connector(connector_id)
    policy = connector.policy()
    if operation in policy.forbidden_operations or operation in FORBIDDEN_GLOBAL:
        raise PermissionError(f"{connector_id} forbids {operation}")
    if connector.status not in INGESTABLE_CONNECTOR_STATUSES and operation in {"ingest", "normalize"}:
        raise PermissionError(f"{connector_id} is {connector.status}, not ingestion-enabled")
    if operation not in policy.allowed_operations and operation not in {"revoke", "health", "policy"}:
        raise PermissionError(f"{connector_id} does not allow {operation}")
