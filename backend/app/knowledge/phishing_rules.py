"""Rule sets for the text & phishing engines.

Curated for the *securities market* context per the SEBI problem statement:
guaranteed-return scams, fake regulator approvals, pump-and-dump, urgency, and
credential-harvesting language. Each rule carries a weight (0..1) representing
how strongly it indicates risk.
"""
from __future__ import annotations

import re

# (compiled regex, weight, human reason) — financial-scam language
FINANCIAL_SCAM_RULES: list[tuple[re.Pattern[str], float, str]] = [
    (re.compile(r"\bguarantee(d|s)?\b.{0,20}\b(return|profit|income|gain)", re.I),
     0.9, "Promises guaranteed returns — a hallmark of investment fraud."),
    (re.compile(r"\b\d{2,3}\s?%\s?(return|profit|gain|monthly|weekly|daily)", re.I),
     0.85, "Advertises unrealistic percentage returns."),
    (re.compile(r"\b(double|triple|10x|100x|multiply)\b.{0,15}\b(money|investment|capital)", re.I),
     0.85, "Claims your money will be multiplied."),
    (re.compile(r"\brisk[- ]?free\b.{0,15}\b(invest|return|profit|trade)", re.I),
     0.8, "Describes the investment as risk-free."),
    (re.compile(r"\b(sebi|nse|bse|rbi)\b.{0,25}\b(approv|certif|guarantee|endors|registered scheme)", re.I),
     0.9, "Falsely implies regulator (SEBI/NSE/BSE/RBI) approval or guarantee."),
    (re.compile(r"\b(sure[- ]?shot|jackpot|multibagger|insider)\b.{0,15}\b(tip|call|stock|pick)", re.I),
     0.8, "Offers 'sure-shot' / insider stock tips."),
    (re.compile(r"\b(pump|target hit|book profit|buy now sell)\b.{0,20}\b(stock|scrip|share)", re.I),
     0.7, "Pump-and-dump style trading exhortation."),
    (re.compile(r"\b(join|enter)\b.{0,15}\b(telegram|whatsapp)\b.{0,20}\b(group|channel)\b.{0,25}\b(profit|tip|call|trade)", re.I),
     0.7, "Recruits into a paid tips Telegram/WhatsApp group."),
    (re.compile(r"\b(crypto|bitcoin|forex|binary option)\b.{0,20}\b(guaranteed|double|profit)", re.I),
     0.75, "High-risk crypto/forex/binary scheme with profit promises."),
]

# Urgency / pressure language
URGENCY_RULES: list[tuple[re.Pattern[str], float, str]] = [
    (re.compile(r"\b(act|invest|pay|respond|click|verify)\b.{0,12}\b(now|immediately|today|fast|quick)", re.I),
     0.7, "Pressures immediate action."),
    (re.compile(r"\b(limited|last|final)\b.{0,10}\b(time|offer|chance|slot|seat)", re.I),
     0.65, "Creates false scarcity ('limited time / last chance')."),
    (re.compile(r"\b(expire|expiring|closing)\b.{0,15}\b(soon|today|hour|minute)", re.I),
     0.6, "Claims the opportunity is expiring imminently."),
    (re.compile(r"\bwithin\s+\d+\s*(min|hour|hr)", re.I),
     0.55, "Imposes a short countdown deadline."),
    (re.compile(r"[!]{2,}", re.I), 0.35, "Excessive exclamation for pressure."),
]

# Credential harvesting / account-threat language
CREDENTIAL_RULES: list[tuple[re.Pattern[str], float, str]] = [
    (re.compile(r"\b(verify|update|confirm|re[- ]?activate)\b.{0,15}\b(account|kyc|pan|demat|bank)", re.I),
     0.8, "Requests account/KYC/PAN verification — classic phishing lure."),
    (re.compile(r"\b(account|demat|trading account)\b.{0,15}\b(block|suspend|freez|deactivat)", re.I),
     0.8, "Threatens account suspension to force action."),
    (re.compile(r"\b(otp|pin|password|cvv|login|credential)\b.{0,15}\b(share|send|enter|provide)", re.I),
     0.9, "Asks you to share OTP/PIN/password/CVV."),
    (re.compile(r"\b(click|open)\b.{0,10}\b(link|below|here)\b.{0,20}\b(login|sign in|verify)", re.I),
     0.7, "Directs to a login link — likely a fake login page."),
]

# High-signal keywords that individually add mild risk.
RISKY_KEYWORDS: dict[str, float] = {
    "guaranteed": 0.4, "lottery": 0.5, "prize": 0.4, "winner": 0.4,
    "congratulations": 0.35, "claim now": 0.5, "free money": 0.6,
    "work from home": 0.3, "part time income": 0.35, "refund": 0.3,
    "wire transfer": 0.4, "gift card": 0.5, "bonus": 0.25,
}

# URL shorteners frequently used to hide destinations.
URL_SHORTENERS: set[str] = {
    "bit.ly", "tinyurl.com", "goo.gl", "t.co", "ow.ly", "is.gd", "buff.ly",
    "cutt.ly", "rebrand.ly", "shorturl.at", "rb.gy", "t.me", "bit.do",
    "tiny.cc", "adf.ly", "shorte.st", "clck.ru",
}

# Suspicious TLDs over-represented in abuse feeds.
SUSPICIOUS_TLDS: set[str] = {
    "zip", "mov", "xyz", "top", "click", "link", "gq", "cf", "ml", "tk",
    "ga", "work", "country", "kim", "loan", "men", "date", "review",
}

URL_RE = re.compile(
    r"\b((?:https?://|www\.)[^\s<>\"')]+|[a-z0-9][a-z0-9\-]{1,}\.[a-z]{2,}(?:/[^\s<>\"')]*)?)",
    re.I,
)
IP_URL_RE = re.compile(r"https?://\d{1,3}(?:\.\d{1,3}){3}")
