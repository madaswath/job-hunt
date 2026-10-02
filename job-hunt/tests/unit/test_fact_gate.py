from jobhunt_tailoring.fact_gate import fact_gate


def test_blocks_invented_metrics():
    out = fact_gate("I increased 40% conversion", ["Built RAG evaluation at current employer"])
    assert out["passed"] is False
    assert out["invented_claims"]


def test_allows_verified_claim():
    facts = ["I increased 40% conversion on search"]
    out = fact_gate("I increased 40% conversion on search", facts)
    assert out["passed"] is True
