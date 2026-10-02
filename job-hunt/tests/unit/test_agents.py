import pytest
from jobhunt_agents.permissions import agent_can_use_tool, assert_agent_permission
from jobhunt_agents.registry import AGENTS


def test_no_direct_db():
    assert not agent_can_use_tool("arjuna", "db_query")
    assert agent_can_use_tool("arjuna", "score_match_v2")


def test_vishwakarma_cannot_bypass():
    with pytest.raises(PermissionError):
        assert_agent_permission("vishwakarma", "transition_inbox", {"bypass_approval": True, "to_state": "applied"})
    with pytest.raises(PermissionError):
        assert_agent_permission("vishwakarma", "transition_inbox", {"to_state": "applied"})


def test_outreach_and_interview_gates():
    with pytest.raises(PermissionError):
        assert_agent_permission("krishna", "create_outreach_draft")
    with pytest.raises(PermissionError):
        assert_agent_permission("skanda", "prepare_interview")
    assert_agent_permission("krishna", "create_outreach_draft", {"explicit_outreach_request": True})
    assert AGENTS["dharma"].status == "live"
    assert AGENTS["saraswati"].status == "live"
