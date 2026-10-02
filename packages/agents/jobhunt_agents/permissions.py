from jobhunt_agents.registry import AGENTS

FORBIDDEN_TOOLS = {"db_query", "sql_execute", "send_email", "submit_application"}


def agent_can_use_tool(agent_name: str, tool: str) -> bool:
    agent = AGENTS[agent_name]
    if tool in FORBIDDEN_TOOLS:
        return False
    if agent.status not in {"live", "contract"} and tool not in agent.allowed_tools:
        return False
    return tool in agent.allowed_tools


def assert_agent_permission(agent_name: str, tool: str, context: dict | None = None) -> None:
    ctx = context or {}
    if not agent_can_use_tool(agent_name, tool):
        raise PermissionError(f"{agent_name} cannot use {tool}")
    if agent_name == "vishwakarma" and tool == "transition_inbox":
        if ctx.get("bypass_approval"):
            raise PermissionError("vishwakarma cannot bypass approval requirements")
        if ctx.get("to_state") in {"tailored", "ready_to_apply", "applied"} and not ctx.get("approval_id"):
            raise PermissionError("approval required for this transition")
    if agent_name in {"hanuman", "krishna"} and not ctx.get("explicit_outreach_request"):
        raise PermissionError("outreach agents require explicit candidate request")
    if agent_name == "skanda" and not ctx.get("interview_stage_recorded"):
        raise PermissionError("skanda requires an interview stage")
    if agent_name == "krishna" and tool == "send_email":
        raise PermissionError("krishna never sends email")
