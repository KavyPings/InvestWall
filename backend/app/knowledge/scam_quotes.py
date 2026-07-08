"""Curated bank of real/representative scam keywords and phrases, specific
to Indian securities-market fraud. Serves two purposes:

1. Source material for expanding RISKY_KEYWORDS / rule patterns in
   phishing_rules.py (this file's SCAM_QUOTE_BANK is folded in below).
2. Few-shot grounding seeds for ml/scripts/generate_synthetic.py, so
   LLM-generated synthetic examples stay anchored to real scam phrasing
   instead of drifting into generic, unrealistic text.

STARTER SET — expand to >=150 entries from SEBI investor-alert pages,
RBI's public cautions list, and cybercrime.gov.in advisories before running
generate_synthetic.py at full scale (see Task 5 of the implementation plan).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ScamQuote:
    text: str
    archetype: str
    note: str


SCAM_QUOTE_BANK: list[ScamQuote] = [
    ScamQuote(
        "Guaranteed 40% returns every month, absolutely risk-free investment.",
        "guaranteed_returns",
        "Classic guaranteed-return pitch pattern.",
    ),
    ScamQuote(
        "SEBI has approved this scheme, your capital is 100% safe.",
        "fake_regulator_approval",
        "False regulator-approval claim.",
    ),
    ScamQuote(
        "Join our exclusive trading circle for consistent, no-loss weekly payouts.",
        "guaranteed_returns",
        "Paraphrase avoiding literal 'guaranteed returns' wording.",
    ),
    ScamQuote(
        "This is risk-free money for you, act before slots close tonight.",
        "guaranteed_returns",
        "Risk-free framing + urgency combined.",
    ),
    ScamQuote(
        "Our insider tip has hit target 9 out of 10 times this month.",
        "insider_tip",
        "Sure-shot/insider stock-tip pattern.",
    ),
    ScamQuote(
        "Double your capital in 15 days with our proven strategy.",
        "guaranteed_returns",
        "Multiply-your-money variant.",
    ),
    ScamQuote(
        "Your demat account will be suspended unless you verify your PAN now.",
        "credential_harvest",
        "Account-suspension threat to force credential disclosure.",
    ),
    ScamQuote(
        "Share the OTP you just received so we can confirm your identity.",
        "credential_harvest",
        "Direct OTP-sharing request.",
    ),
    ScamQuote(
        "Limited seats left in our VIP Telegram tips group, first month free.",
        "telegram_recruit",
        "Tips-group recruitment with false scarcity.",
    ),
    ScamQuote(
        "This penny stock is about to explode, insiders are already buying.",
        "pump_and_dump",
        "Pump-and-dump exhortation.",
    ),
    ScamQuote(
        "Convert your savings into a daily-payout crypto plan, withdraw profits every day.",
        "crypto_scheme",
        "Daily-payout crypto scheme pattern.",
    ),
    ScamQuote(
        "Congratulations, you've been selected for a government-backed wealth scheme.",
        "fake_regulator_approval",
        "Fake selection/eligibility framing.",
    ),
]

# Keyword -> weight additions derived from the quote bank above, folded into
# phishing_rules.RISKY_KEYWORDS. Weights follow the same 0..1 convention.
KEYWORD_ADDITIONS: dict[str, float] = {
    "risk-free money": 0.5,
    "no-loss": 0.45,
    "consistent payouts": 0.35,
    "double your capital": 0.5,
    "insider tip": 0.45,
    "sure-shot": 0.4,
    "daily-payout": 0.4,
    "vip telegram": 0.35,
    "government-backed wealth scheme": 0.45,
}
