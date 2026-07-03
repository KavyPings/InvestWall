"""Module 5 — Phishing Detection Engine (PRD §6).

Focuses on the *URL / domain / sender* dimension of phishing (the text engine
covers scam language). Checks: malicious/shortened/raw-IP URLs, look-alike and
typosquat domains impersonating official brands, suspicious TLDs, and sender
impersonation. Pure-Python (tldextract) — no network required.
"""
from __future__ import annotations

import logging
import re

from app.core.evidence import Component, EvidenceBundle, Modality
from app.engines.base import Engine, Payload
from app.knowledge.financial_domains import BRAND_TOKENS, is_official
from app.knowledge.phishing_rules import (
    IP_URL_RE,
    SUSPICIOUS_TLDS,
    URL_RE,
    URL_SHORTENERS,
)

logger = logging.getLogger("investwall.engine.phishing")

_tldextract = None
_TLD_TRIED = False


def _get_tldextract():
    global _tldextract, _TLD_TRIED
    if _tldextract is not None or _TLD_TRIED:
        return _tldextract
    _TLD_TRIED = True
    try:
        import tldextract

        # Offline extractor: don't fetch the public-suffix list over the network.
        _tldextract = tldextract.TLDExtract(suffix_list_urls=())
    except Exception:  # pragma: no cover
        _tldextract = None
    return _tldextract


def _levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def extract_urls(text: str) -> list[str]:
    urls: list[str] = []
    for m in URL_RE.finditer(text or ""):
        raw = m.group(1).rstrip(".,);]'\"")
        # Skip bare decimals / version strings.
        if re.fullmatch(r"[\d.]+", raw):
            continue
        urls.append(raw)
    return list(dict.fromkeys(urls))  # dedupe, keep order


def registered_domain(url: str) -> str:
    ext = _get_tldextract()
    host = re.sub(r"^\w+://", "", url).split("/")[0].split("?")[0].lower()
    if ext is not None:
        r = ext(host)
        if r.domain and r.suffix:
            return f"{r.domain}.{r.suffix}"
        return host
    # Fallback: last two labels.
    parts = host.split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else host


class PhishingEngine(Engine):
    name = "phishing"

    def analyze(self, payload: Payload) -> EvidenceBundle:
        bundle = self._bundle(payload.modality or Modality.TEXT)
        text = payload.text or ""
        urls = extract_urls(text)
        bundle.extras["urls"] = urls

        for url in urls:
            self._score_url(bundle, url)

        # Sender impersonation (if a sender/email is supplied).
        self._score_sender(bundle, payload)
        return bundle

    def _score_url(self, bundle: EvidenceBundle, url: str) -> None:
        low = url.lower()
        dom = registered_domain(url)

        if is_official(dom):
            return  # official link — handled (positively) by authenticity engine

        if IP_URL_RE.match(low):
            bundle.add("ip_url", 0.85,
                       f"Link uses a raw IP address ({dom}) instead of a domain.",
                       Component.PHISHING, weight=1.1, url=url)

        if dom in URL_SHORTENERS:
            bundle.add("url_shortener", 0.7,
                       f"Uses a URL shortener ({dom}) that hides the real destination.",
                       Component.PHISHING, weight=1.0, url=url)

        tld = dom.rsplit(".", 1)[-1] if "." in dom else ""
        if tld in SUSPICIOUS_TLDS:
            bundle.add("suspicious_tld", 0.6,
                       f"Domain uses a high-abuse TLD (.{tld}).",
                       Component.PHISHING, weight=0.8, url=url)

        # Look-alike / typosquat against official brands.
        core = dom.split(".")[0]
        for token in BRAND_TOKENS:
            if token in core and not is_official(dom):
                dist = _levenshtein(core, token)
                if core != token and (token in core or dist <= 2):
                    bundle.add("brand_impersonation", 0.9,
                               f"Domain '{dom}' mimics the official brand '{token}'.",
                               Component.PHISHING, weight=1.2, url=url, brand=token)
                    break

        if re.search(r"(login|verify|secure|account|update|kyc)", low) and (
            dom in URL_SHORTENERS or tld in SUSPICIOUS_TLDS or IP_URL_RE.match(low)
        ):
            bundle.add("fake_login_link", 0.75,
                       "Link text suggests a login/verification page on an untrusted host.",
                       Component.PHISHING, weight=1.0, url=url)

        # Excessive subdomains / '@' obfuscation.
        if low.count("@") and re.search(r"https?://[^/@\s]*@", low):
            bundle.add("url_obfuscation", 0.7,
                       "URL contains an '@' that can disguise the true destination.",
                       Component.PHISHING, weight=0.9, url=url)
        if re.sub(r"^\w+://", "", low).split("/")[0].count(".") >= 4:
            bundle.add("subdomain_stuffing", 0.5,
                       "Excessive subdomains — a common obfuscation tactic.",
                       Component.PHISHING, weight=0.7, url=url)

    def _score_sender(self, bundle: EvidenceBundle, payload: Payload) -> None:
        sender = (payload.sender or "").strip().lower()
        if "@" not in sender:
            return
        dom = sender.split("@")[-1]
        rdom = registered_domain(dom)
        # Claims an official brand in the local part but not the domain.
        local = sender.split("@")[0]
        for token in BRAND_TOKENS:
            if token in local and not is_official(rdom):
                bundle.add("sender_impersonation", 0.85,
                           f"Sender name references '{token}' but the domain "
                           f"'{rdom}' is not official.",
                           Component.SOURCE, weight=1.1, sender=sender)
                return
        # Free-mail sender claiming to be an institution.
        if rdom in {"gmail.com", "outlook.com", "yahoo.com", "hotmail.com"} and any(
            t in local for t in BRAND_TOKENS
        ):
            bundle.add("freemail_institution", 0.7,
                       f"Institutional-sounding sender using a free email domain ({rdom}).",
                       Component.SOURCE, weight=0.9, sender=sender)
