import re

CLAIM_PATTERNS = (
    r"increased\s+\d+%",
    r"led a team of\s+\d+",
    r"authored",
    r"patented",
    r"phd",
    r"i founded",
    r"\b\d+\s*years?\s+at\b",
)

EDUCATION_TOKENS = ("phd", "mba", "b.tech", "m.tech", "bachelor", "master", "iit", "nit")


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower())


def _allowed_corpus(verified_facts: list[str], profile_bits: list[str]) -> str:
    return _normalize(" ".join(verified_facts + profile_bits))


def fact_gate(generated_text: str, verified_facts: list[str], profile_bits: list[str] | None = None) -> dict:
    text = generated_text or ""
    corpus = _allowed_corpus(verified_facts, profile_bits or [])
    invented: list[str] = []

    for pattern in CLAIM_PATTERNS:
        for match in re.finditer(pattern, text, flags=re.I):
            snippet = match.group(0)
            if _normalize(snippet) not in corpus and not any(_normalize(snippet) in _normalize(f) for f in verified_facts):
                invented.append(snippet)

    for token in EDUCATION_TOKENS:
        if re.search(rf"\b{re.escape(token)}\b", text, flags=re.I):
            if token not in corpus:
                invented.append(token)

    # Flag employer-like phrases " at CompanyName" if CompanyName not in corpus
    for match in re.finditer(r"\bat\s+([A-Z][A-Za-z0-9&.\-]{2,})\b", text):
        employer = match.group(1)
        if _normalize(employer) not in corpus:
            invented.append(f"at {employer}")

    passed = not invented
    return {"passed": passed, "invented_claims": sorted(set(invented)), "status": "ready" if passed else "blocked"}
