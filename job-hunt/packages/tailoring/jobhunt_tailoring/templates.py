"""Deterministic document templates — verified strings only."""


def build_cv_variant(full_name: str, headline: str, facts: list[str], job_title: str, company: str) -> str:
    lines = [
        f"# {full_name or 'Candidate'}",
        headline or "",
        "",
        f"Tailored for: {job_title} at {company or 'Employer'}",
        "",
        "## Verified facts",
    ]
    for fact in facts:
        lines.append(f"- {fact}")
    return "\n".join(line for line in lines if line is not None)


def build_cover_letter(full_name: str, facts: list[str], job_title: str, company: str, excerpt: str) -> str:
    intro = f"Dear Hiring Team at {company or 'the company'},\n\n"
    body = f"I am applying for the {job_title} role. "
    if excerpt:
        body += f"From the posting: {excerpt[:400]}\n\n"
    body += "Verified background:\n"
    for fact in facts[:12]:
        body += f"- {fact}\n"
    body += f"\nRegards,\n{full_name or 'Candidate'}"
    return intro + body


def build_application_answers(facts: list[str], job_title: str) -> str:
    return f"Role: {job_title}\n\nWhy fit (verified facts only):\n" + "\n".join(f"- {f}" for f in facts[:8])
