package com.investwall.app.local

/**
 * On-device knowledge base — a Kotlin port of the backend's
 * `knowledge/phishing_rules.py` and `financial_domains.py`.
 *
 * This lets text / SMS be screened entirely on the phone (privacy-first: the
 * content never leaves the device for the quick check). The heavier ML models
 * remain server-side and are only used for the opt-in "Deep AI check".
 */

data class Rule(val regex: Regex, val weight: Double, val reason: String)

private fun ci(pattern: String) = Regex(pattern, RegexOption.IGNORE_CASE)

object LocalKnowledge {

    // --- Financial-scam language ---
    val financialScamRules = listOf(
        Rule(ci("""\bguarantee(d|s)?\b.{0,20}\b(return|profit|income|gain)"""), 0.9,
            "Promises guaranteed returns — a hallmark of investment fraud."),
        Rule(ci("""\b\d{2,3}\s?%\s?(return|profit|gain|monthly|weekly|daily)"""), 0.85,
            "Advertises unrealistic percentage returns."),
        Rule(ci("""\b(double|triple|10x|100x|multiply)\b.{0,15}\b(money|investment|capital)"""), 0.85,
            "Claims your money will be multiplied."),
        Rule(ci("""\brisk[- ]?free\b.{0,15}\b(invest|return|profit|trade)"""), 0.8,
            "Describes the investment as risk-free."),
        Rule(ci("""\b(sebi|nse|bse|rbi)\b.{0,25}\b(approv|certif|guarantee|endors|registered scheme)"""), 0.9,
            "Falsely implies regulator (SEBI/NSE/BSE/RBI) approval or guarantee."),
        Rule(ci("""\b(sure[- ]?shot|jackpot|multibagger|insider)\b.{0,15}\b(tip|call|stock|pick)"""), 0.8,
            "Offers 'sure-shot' / insider stock tips."),
        Rule(ci("""\b(pump|target hit|book profit|buy now sell)\b.{0,20}\b(stock|scrip|share)"""), 0.7,
            "Pump-and-dump style trading exhortation."),
        Rule(ci("""\b(join|enter)\b.{0,15}\b(telegram|whatsapp)\b.{0,20}\b(group|channel)"""), 0.65,
            "Recruits into a tips Telegram/WhatsApp group."),
        Rule(ci("""\b(crypto|bitcoin|forex|binary option)\b.{0,20}\b(guaranteed|double|profit)"""), 0.75,
            "High-risk crypto/forex/binary scheme with profit promises."),
    )

    // --- Urgency / pressure ---
    val urgencyRules = listOf(
        Rule(ci("""\b(act|invest|pay|respond|click|verify)\b.{0,12}\b(now|immediately|today|fast|quick)"""), 0.7,
            "Pressures immediate action."),
        Rule(ci("""\b(limited|last|final)\b.{0,10}\b(time|offer|chance|slot|seat)"""), 0.65,
            "Creates false scarcity ('limited time / last chance')."),
        Rule(ci("""\b(expire|expiring|closing)\b.{0,15}\b(soon|today|hour|minute)"""), 0.6,
            "Claims the opportunity is expiring imminently."),
        Rule(ci("""\bwithin\s+\d+\s*(min|hour|hr)"""), 0.55,
            "Imposes a short countdown deadline."),
        Rule(ci("""[!]{2,}"""), 0.35, "Excessive exclamation for pressure."),
    )

    // --- Credential harvesting / account threats ---
    val credentialRules = listOf(
        Rule(ci("""\b(verify|update|confirm|re[- ]?activate)\b.{0,15}\b(account|kyc|pan|demat|bank)"""), 0.8,
            "Requests account/KYC/PAN verification — classic phishing lure."),
        Rule(ci("""\b(account|demat|trading account)\b.{0,15}\b(block|suspend|freez|deactivat)"""), 0.8,
            "Threatens account suspension to force action."),
        Rule(ci("""\b(otp|pin|password|cvv|login|credential)\b.{0,15}\b(share|send|enter|provide)"""), 0.9,
            "Asks you to share OTP/PIN/password/CVV."),
        Rule(ci("""\b(click|open)\b.{0,10}\b(link|below|here)\b.{0,20}\b(login|sign in|verify)"""), 0.7,
            "Directs to a login link — likely a fake login page."),
    )

    val riskyKeywords: Map<String, Double> = mapOf(
        "guaranteed" to 0.4, "lottery" to 0.5, "prize" to 0.4, "winner" to 0.4,
        "congratulations" to 0.35, "claim now" to 0.5, "free money" to 0.6,
        "work from home" to 0.3, "part time income" to 0.35, "refund" to 0.3,
        "wire transfer" to 0.4, "gift card" to 0.5, "bonus" to 0.25,
    )

    val urlShorteners: Set<String> = setOf(
        "bit.ly", "tinyurl.com", "goo.gl", "t.co", "ow.ly", "is.gd", "buff.ly",
        "cutt.ly", "rebrand.ly", "shorturl.at", "rb.gy", "t.me", "bit.do",
        "tiny.cc", "adf.ly", "shorte.st", "clck.ru",
    )

    val suspiciousTlds: Set<String> = setOf(
        "zip", "mov", "xyz", "top", "click", "link", "gq", "cf", "ml", "tk",
        "ga", "work", "country", "kim", "loan", "men", "date", "review",
    )

    // --- Official Indian securities-market domains ---
    val officialDomains: Map<String, String> = mapOf(
        "sebi.gov.in" to "Securities and Exchange Board of India (SEBI)",
        "nseindia.com" to "National Stock Exchange (NSE)",
        "bseindia.com" to "BSE Ltd (Bombay Stock Exchange)",
        "cdslindia.com" to "Central Depository Services (CDSL)",
        "nsdl.co.in" to "National Securities Depository (NSDL)",
        "rbi.org.in" to "Reserve Bank of India (RBI)",
        "amfiindia.com" to "Association of Mutual Funds in India (AMFI)",
        "zerodha.com" to "Zerodha (registered broker)",
        "groww.in" to "Groww (registered broker)",
        "upstox.com" to "Upstox (registered broker)",
        "icicidirect.com" to "ICICI Direct (registered broker)",
        "kotaksecurities.com" to "Kotak Securities (registered broker)",
        "angelone.in" to "Angel One (registered broker)",
    )

    val brandTokens: Set<String> = setOf(
        "sebi", "nse", "nseindia", "bse", "bseindia", "cdsl", "nsdl", "rbi",
        "zerodha", "groww", "upstox", "icici", "kotak", "angelone", "amfi",
    )

    val urlRegex = ci("""(https?://\S+|www\.\S+|\b[a-z0-9][a-z0-9\-]*\.[a-z]{2,}(?:/\S*)?)""")
    val ipUrlRegex = ci("""https?://\d{1,3}(\.\d{1,3}){3}""")
    // An authority *claim* = the message frames itself as an official
    // communication, not merely mentioning a regulator. "SEBI is my goat" must
    // NOT match; "official SEBI circular" / "SEBI approved scheme" should.
    val claimAuthorityRegex = ci(
        """\b(?:from the desk of""" +
        """|official\s+(?:notice|circular|announcement|communication|update|alert|advisory)""" +
        """|(?:sebi|nse|bse|rbi|nsdl|cdsl|amfi)\b.{0,15}\b(?:registered|approved|certified|verified|circular|notice|order|directive|registration|guideline|scheme|clearance|endorsed|authori[sz]ed)""" +
        """|(?:registered|approved|certified|verified|endorsed|cleared|authori[sz]ed)\b.{0,15}\bby\s+(?:sebi|nse|bse|rbi|nsdl|cdsl|amfi)""" +
        """|(?:this is|on behalf of|issued by|message from|notice from|update from)\s+(?:the\s+)?(?:sebi|nse|bse|rbi|nsdl|cdsl|amfi))\b""",
    )

    fun isOfficial(domain: String): String? {
        val d = domain.lowercase().trim().trimEnd('.')
        for ((official, org) in officialDomains) {
            if (d == official || d.endsWith(".$official")) return org
        }
        return null
    }
}
