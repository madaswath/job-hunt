def normalize_ctc_inr_annual(
    amount: float | int | None,
    period: str | None = "annual",
) -> float | None:
    if amount is None:
        return None
    value = float(amount)
    period_norm = (period or "annual").lower()
    if period_norm in {"month", "monthly", "pm", "per_month"}:
        return value * 12
    if period_norm in {"lpa", "lakhs", "lakh"}:
        return value * 100_000
    return value
