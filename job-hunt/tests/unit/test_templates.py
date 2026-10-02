from jobhunt_tailoring.fact_gate import fact_gate
from jobhunt_tailoring.templates import build_cv_variant


def test_templates_only_use_provided_strings():
    facts = ["Built RAG evaluation at current employer"]
    cv = build_cv_variant("Asha", "AI engineer", facts, "GenAI Engineer", "Example Labs")
    assert "Asha" in cv
    assert facts[0] in cv
    assert "InventedCorp" not in cv


def test_fact_gate_blocks_unknown_employer():
    text = "I previously worked at InventedCorp on ML."
    out = fact_gate(text, ["Built RAG evaluation"], ["Asha"])
    assert out["passed"] is False
    assert out["invented_claims"]
