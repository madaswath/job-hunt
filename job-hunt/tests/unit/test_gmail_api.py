from unittest.mock import MagicMock, patch

from jobhunt_connectors.gmail_api import fetch_labeled_messages


@patch("jobhunt_connectors.gmail_api.httpx.Client")
def test_fetch_deduplicates_message_ids(mock_client_cls):
    client = mock_client_cls.return_value.__enter__.return_value
    list_res = MagicMock()
    list_res.status_code = 200
    list_res.json.return_value = {"messages": [{"id": "m1"}, {"id": "m1"}]}
    msg_res = MagicMock()
    msg_res.status_code = 200
    msg_res.json.return_value = {
        "id": "m1",
        "snippet": "Apply https://example.com/jobs/1",
        "payload": {"headers": [{"name": "Subject", "value": "Job alert"}], "body": {}},
    }
    client.request.side_effect = [list_res, msg_res]
    items, _ = fetch_labeled_messages("token", ["JobAlerts"], max_messages=5, seen_ids=set())
    assert len(items) == 1
    assert items[0]["external_id"] == "m1"
