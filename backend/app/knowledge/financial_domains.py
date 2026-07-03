"""Registry of official Indian securities-market domains and organisations.

Used by the Authenticity Verification Engine to (a) raise trust when a
communication genuinely originates from an official domain and (b) detect
look-alike / impersonation domains that mimic these brands.
"""
from __future__ import annotations

# Canonical official domains of regulators, exchanges, depositories and major
# registered intermediaries. Extend as needed / back with a real registry later.
OFFICIAL_DOMAINS: dict[str, str] = {
    "sebi.gov.in": "Securities and Exchange Board of India (SEBI)",
    "nseindia.com": "National Stock Exchange (NSE)",
    "bseindia.com": "BSE Ltd (Bombay Stock Exchange)",
    "cdslindia.com": "Central Depository Services (CDSL)",
    "nsdl.co.in": "National Securities Depository (NSDL)",
    "rbi.org.in": "Reserve Bank of India (RBI)",
    "mca.gov.in": "Ministry of Corporate Affairs",
    "amfiindia.com": "Association of Mutual Funds in India (AMFI)",
    "npci.org.in": "National Payments Corporation of India (NPCI)",
    "incometax.gov.in": "Income Tax Department",
    "zerodha.com": "Zerodha (registered broker)",
    "groww.in": "Groww (registered broker)",
    "upstox.com": "Upstox (registered broker)",
    "icicidirect.com": "ICICI Direct (registered broker)",
    "kotaksecurities.com": "Kotak Securities (registered broker)",
    "angelone.in": "Angel One (registered broker)",
}

# Brand tokens used to spot look-alike / typosquat domains.
BRAND_TOKENS: set[str] = {
    "sebi", "nse", "nseindia", "bse", "bseindia", "cdsl", "nsdl", "rbi",
    "zerodha", "groww", "upstox", "icici", "kotak", "angelone", "amfi",
}


def is_official(domain: str) -> str | None:
    """Return the org name if *domain* (or a subdomain of it) is official."""
    domain = (domain or "").lower().strip().rstrip(".")
    for official, org in OFFICIAL_DOMAINS.items():
        if domain == official or domain.endswith("." + official):
            return org
    return None
