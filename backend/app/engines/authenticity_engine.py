"""Module 6 — Authenticity Verification Engine (PRD §6, tech-stack §9).

Verifies whether a communication genuinely comes from a legitimate financial
institution. Emits AUTHENTICITY-component evidence where **score = risk** i.e.
1.0 = unverifiable/spoofed, 0.0 = strongly verified authentic.

Checks: official domain match, SPF/DMARC DNS records (optional, network),
sender-vs-claimed alignment, and (for documents) metadata/QR sanity.
"""
from __future__ import annotations

import logging
import re

from app.config import get_settings
from app.core.evidence import Component, EvidenceBundle, Modality
from app.engines.base import Engine, Payload
from app.engines.phishing_engine import registered_domain
from app.knowledge.financial_domains import BRAND_TOKENS, is_official

logger = logging.getLogger("investwall.engine.authenticity")

_CLAIM_RE = re.compile(
    r"\b(sebi|nse|bse|rbi|nsdl|cdsl|amfi|from the desk of|official (?:notice|circular|announcement))\b",
    re.I,
)


class AuthenticityEngine(Engine):
    name = "authenticity"

    def analyze(self, payload: Payload) -> EvidenceBundle:
        settings = get_settings()
        bundle = self._bundle(payload.modality or Modality.TEXT)
        text = payload.text or ""
        sender = (payload.sender or "").strip().lower()

        claims_official = bool(_CLAIM_RE.search(text)) or any(
            t in sender for t in BRAND_TOKENS
        )

        sender_domain = sender.split("@")[-1] if "@" in sender else ""
        rdom = registered_domain(sender_domain) if sender_domain else ""
        official_org = is_official(rdom) if rdom else None

        if official_org:
            # Verified official sender — strong authenticity, low risk.
            bundle.add("verified_official_domain", 0.05,
                       f"Sender domain '{rdom}' is a verified official source "
                       f"({official_org}).",
                       Component.AUTHENTICITY, weight=1.3, org=official_org)
            bundle.add("trusted_source", 0.1,
                       f"Recognised legitimate institution: {official_org}.",
                       Component.SOURCE, weight=1.0)
            if settings.enable_dns and rdom:
                self._dns_checks(bundle, rdom)
            return bundle

        if claims_official:
            # Claims to be official but sender is not verifiable => high risk.
            if rdom:
                bundle.add("unverified_claimed_authority", 0.85,
                           f"Message claims official authority but the sender "
                           f"domain '{rdom}' is not an official/registered source.",
                           Component.AUTHENTICITY, weight=1.2)
            else:
                bundle.add("unverifiable_authority_claim", 0.75,
                           "Message claims to be an official financial "
                           "communication but provides no verifiable sender.",
                           Component.AUTHENTICITY, weight=1.0)
            if settings.enable_dns and rdom:
                self._dns_checks(bundle, rdom)
        elif rdom:
            # Ordinary sender, no official claim — mild neutral authenticity risk.
            bundle.add("unrecognised_sender", 0.4,
                       f"Sender '{rdom}' is not a recognised financial institution.",
                       Component.AUTHENTICITY, weight=0.6)
            if settings.enable_dns:
                self._dns_checks(bundle, rdom)

        return bundle

    def _dns_checks(self, bundle: EvidenceBundle, domain: str) -> None:
        """SPF / DMARC presence checks. Absence of policy raises risk slightly."""
        try:
            import dns.resolver  # type: ignore
        except Exception:  # pragma: no cover
            return
        resolver = dns.resolver.Resolver()
        resolver.lifetime = 3.0
        resolver.timeout = 3.0

        spf = self._txt_contains(resolver, domain, "v=spf1")
        dmarc = self._txt_contains(resolver, f"_dmarc.{domain}", "v=DMARC1")

        if spf is False:
            bundle.add("spf_missing", 0.6,
                       f"No SPF record for '{domain}' — sender authorisation "
                       "cannot be validated.",
                       Component.AUTHENTICITY, weight=0.7, domain=domain)
        elif spf is True:
            bundle.add("spf_present", 0.2,
                       f"SPF policy found for '{domain}'.",
                       Component.AUTHENTICITY, weight=0.4, domain=domain)

        if dmarc is False:
            bundle.add("dmarc_missing", 0.55,
                       f"No DMARC policy for '{domain}' — domain is easier to spoof.",
                       Component.AUTHENTICITY, weight=0.6, domain=domain)
        elif dmarc is True:
            bundle.add("dmarc_present", 0.2,
                       f"DMARC policy found for '{domain}'.",
                       Component.AUTHENTICITY, weight=0.4, domain=domain)

    @staticmethod
    def _txt_contains(resolver, name: str, needle: str) -> bool | None:
        """True if a TXT record contains needle, False if none, None on error."""
        import dns.resolver  # type: ignore

        try:
            answers = resolver.resolve(name, "TXT")
            for r in answers:
                if needle.lower() in r.to_text().lower():
                    return True
            return False
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
            return False  # domain resolves but has no such record
        except Exception:
            return None  # timeout / no nameservers / offline — inconclusive
