"""Phase 2 API e2e: profile → scan → approve prepare → documents → ready → handoff."""

from jobhunt_worker.loop import run_once


def test_phase2_happy_path(client, auth_a):
    client.put(
        "/api/v1/profile",
        headers=auth_a,
        json={
            "skills": ["python", "rag", "fastapi"],
            "target_titles": ["GenAI Engineer"],
            "preferred_cities": ["Bengaluru", "remote"],
            "verified_facts": [{"kind": "skill", "value": "python"}],
            "trigger_rematch": False,
        },
    )
    client.post("/api/v1/discovery/scans", json={"connector_id": "public_ats_fixture"}, headers=auth_a)
    run_once()
    item = client.get("/api/v1/inbox", headers=auth_a).json()["items"][0]
    assert item.get("captured_text") or item.get("excerpt")
    item_id = item["id"]
    client.post(f"/api/v1/inbox/{item_id}/actions", json={"action": "prepare_application"}, headers=auth_a)
    task = next(t for t in client.get("/api/v1/approvals", headers=auth_a).json()["pending"] if t["inbox_item_id"] == item_id)
    gen = client.post(f"/api/v1/approvals/{task['id']}/decide", json={"decision": "approved"}, headers=auth_a)
    assert gen.status_code == 200
    assert client.get("/api/v1/documents", headers=auth_a).json()["items"]
    client.post(f"/api/v1/inbox/{item_id}/actions", json={"action": "request_draft_approval"}, headers=auth_a)
    draft = next(t for t in client.get("/api/v1/approvals", headers=auth_a).json()["pending"] if t["kind"] == "approve_draft")
    client.post(f"/api/v1/approvals/{draft['id']}/decide", json={"decision": "approved"}, headers=auth_a)
    assert client.get(f"/api/v1/inbox/{item_id}", headers=auth_a).json()["item"]["state"] == "ready_to_apply"
    assert client.post(f"/api/v1/inbox/{item_id}/handoff", headers=auth_a).status_code == 200
    assert client.post("/api/v1/documents/generate", headers=auth_a, json={"inbox_item_id": item_id, "approval_task_id": task["id"]}).status_code in {200, 403}
