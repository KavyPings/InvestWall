package com.investwall.app.local

import com.investwall.app.domain.model.EvidenceItem
import com.investwall.app.domain.model.ScoreComponent
import com.investwall.app.domain.model.TrustBand
import com.investwall.app.domain.model.TrustReport
import java.util.UUID
import kotlin.math.abs
import kotlin.math.max
import kotlin.math.min
import kotlin.math.roundToInt

/**
 * On-device text/phishing analyzer. Mirrors the backend pipeline (text +
 * phishing + authenticity engines → evidence fusion → trust score → template
 * explanation) using only rules — no ML, no network. Produces the same
 * [TrustReport] the UI renders for server results.
 *
 * `llmProvider = "on-device"` marks a report as locally produced; such reports
 * can be escalated to the server via a "Deep AI check".
 */
object LocalAnalyzer {

    // Fusion weights — identical to backend core/fusion.py (PRD §8).
    private val weights = mapOf(
        ScoreComponent.AI to 0.30,
        ScoreComponent.PHISHING to 0.25,
        ScoreComponent.SOURCE to 0.15,
        ScoreComponent.AUTHENTICITY to 0.20,
        ScoreComponent.METADATA to 0.10,
    )

    private data class Sig(
        val signal: String,
        val component: ScoreComponent,
        val score: Double,
        val reason: String,
        val weight: Double = 1.0,
    )

    fun analyze(text: String, source: String? = "manual", sender: String? = null): TrustReport {
        val clean = text.trim().replace(Regex("\\s+"), " ")
        val sigs = mutableListOf<Sig>()

        // --- Rule-based scam / urgency / credential ---
        applyRules(sigs, clean, LocalKnowledge.financialScamRules, ScoreComponent.PHISHING, "scam")
        applyRules(sigs, clean, LocalKnowledge.credentialRules, ScoreComponent.PHISHING, "credential")
        applyRules(sigs, clean, LocalKnowledge.urgencyRules, ScoreComponent.PHISHING, "urgency", 0.7)
        applyKeywords(sigs, clean)

        // --- URLs ---
        scoreUrls(sigs, clean)

        // --- Authenticity (claims to be official?) ---
        scoreAuthenticity(sigs, clean, sender)

        // --- Clean baseline (no phishing signals) ---
        if (sigs.none { it.component == ScoreComponent.PHISHING } && clean.isNotEmpty()) {
            val words = Regex("[A-Za-z']+").findAll(clean).count()
            val baseline = if (words < 3) 0.2 else 0.12
            sigs += Sig("no_phishing_indicators", ScoreComponent.PHISHING, baseline,
                "No phishing, scam, or urgency indicators were detected in the text.", 0.5)
        }

        return fuse(sigs, clean, source, sender)
    }

    // ---- rules ----
    private fun applyRules(
        out: MutableList<Sig>, text: String, rules: List<Rule>,
        component: ScoreComponent, tag: String, weight: Double = 1.0,
    ) {
        for (r in rules) {
            if (r.regex.containsMatchIn(text)) {
                out += Sig("${tag}_rule", component, r.weight, r.reason, weight)
            }
        }
    }

    private fun applyKeywords(out: MutableList<Sig>, text: String) {
        val lower = text.lowercase()
        val hits = LocalKnowledge.riskyKeywords.filterKeys { lower.contains(it) }
        if (hits.isNotEmpty()) {
            val topScore = min(hits.values.max() + 0.05 * (hits.size - 1), 1.0)
            out += Sig("risky_keywords", ScoreComponent.PHISHING, topScore,
                "Contains high-risk terms: ${hits.keys.sorted().joinToString(", ")}.", 0.6)
        }
    }

    // ---- urls ----
    private fun scoreUrls(out: MutableList<Sig>, text: String) {
        val urls = LocalKnowledge.urlRegex.findAll(text)
            .map { it.value.trimEnd('.', ',', ')', ';', ']', '\'', '"') }
            .filterNot { it.matches(Regex("[\\d.]+")) }
            .distinct().toList()

        for (url in urls) {
            val low = url.lowercase()
            val dom = registeredDomain(url)
            if (LocalKnowledge.isOfficial(dom) != null) continue

            if (LocalKnowledge.ipUrlRegex.containsMatchIn(low)) {
                out += Sig("ip_url", ScoreComponent.PHISHING, 0.85,
                    "Link uses a raw IP address ($dom) instead of a domain.", 1.1)
            }
            if (dom in LocalKnowledge.urlShorteners) {
                out += Sig("url_shortener", ScoreComponent.PHISHING, 0.7,
                    "Uses a URL shortener ($dom) that hides the real destination.", 1.0)
            }
            val tld = if ("." in dom) dom.substringAfterLast('.') else ""
            if (tld in LocalKnowledge.suspiciousTlds) {
                out += Sig("suspicious_tld", ScoreComponent.PHISHING, 0.6,
                    "Domain uses a high-abuse TLD (.$tld).", 0.8)
            }
            val core = dom.substringBefore('.')
            for (token in LocalKnowledge.brandTokens) {
                if (core.contains(token) && core != token) {
                    out += Sig("brand_impersonation", ScoreComponent.PHISHING, 0.9,
                        "Domain '$dom' mimics the official brand '$token'.", 1.2)
                    break
                } else if (core != token && levenshtein(core, token) <= 2 && token.length > 3) {
                    out += Sig("brand_impersonation", ScoreComponent.PHISHING, 0.9,
                        "Domain '$dom' closely resembles the official brand '$token'.", 1.2)
                    break
                }
            }
        }
    }

    // ---- authenticity ----
    private fun scoreAuthenticity(out: MutableList<Sig>, text: String, sender: String?) {
        val senderLow = (sender ?: "").trim().lowercase()
        val senderDom = if ("@" in senderLow) registeredDomain(senderLow.substringAfterLast('@')) else ""
        val org = if (senderDom.isNotEmpty()) LocalKnowledge.isOfficial(senderDom) else null

        if (org != null) {
            out += Sig("verified_official_domain", ScoreComponent.AUTHENTICITY, 0.05,
                "Sender domain '$senderDom' is a verified official source ($org).", 1.3)
            out += Sig("trusted_source", ScoreComponent.SOURCE, 0.1,
                "Recognised legitimate institution: $org.", 1.0)
            return
        }

        val claimsOfficial = LocalKnowledge.claimAuthorityRegex.containsMatchIn(text) ||
            LocalKnowledge.brandTokens.any { senderLow.contains(it) }
        if (claimsOfficial) {
            if (senderDom.isNotEmpty()) {
                out += Sig("unverified_claimed_authority", ScoreComponent.AUTHENTICITY, 0.85,
                    "Message claims official authority but the sender domain '$senderDom' is not official.", 1.2)
            } else {
                out += Sig("unverifiable_authority_claim", ScoreComponent.AUTHENTICITY, 0.75,
                    "Message claims to be an official financial communication but provides no verifiable sender.", 1.0)
            }
        }
    }

    // ---- fusion ----
    private fun fuse(sigs: List<Sig>, clean: String, source: String?, sender: String?): TrustReport {
        val present = ScoreComponent.entries.mapNotNull { comp ->
            val items = sigs.filter { it.component == comp }
            if (items.isEmpty()) null else comp to componentScore(items)
        }.toMap()

        val trustScore: Int
        val band: TrustBand
        val confidence: Double
        var primaryThreat: String? = null

        if (present.isEmpty()) {
            trustScore = 50; band = TrustBand.fromScore(50); confidence = 0.1
        } else {
            val totalWeight = present.keys.sumOf { weights.getValue(it) }
            var risk = present.entries.sumOf { (c, s) -> s * (weights.getValue(c) / totalWeight) }
            val strongest = present.values.max()
            risk = max(risk, strongest * 0.6)
            trustScore = ((1.0 - risk) * 100).roundToInt().coerceIn(0, 100)
            band = TrustBand.fromScore(trustScore)
            confidence = confidenceOf(present, sigs.size)
            primaryThreat = primaryThreatOf(present)
        }

        val evidence = sigs.sortedByDescending { it.score }.map {
            EvidenceItem(it.signal, it.component.key, it.score.toFloat(), it.reason)
        }
        val explanation = LocalExplainer.explain(band, trustScore, confidence, primaryThreat, evidence)

        return TrustReport(
            id = UUID.randomUUID().toString().replace("-", ""),
            createdAt = System.currentTimeMillis(),
            modality = "text",
            source = source,
            sender = sender,
            filename = null,
            inputPreview = clean,          // kept locally only; never uploaded
            trustScore = trustScore,
            band = band,
            confidence = confidence.toFloat(),
            primaryThreat = primaryThreat,
            componentScores = present.mapKeys { it.key.key }.mapValues { it.value.toFloat() },
            explanation = explanation,
            llmProvider = "on-device",
            evidence = evidence,
        )
    }

    private fun componentScore(items: List<Sig>): Double {
        val totalW = items.sumOf { it.weight }.takeIf { it > 0 } ?: 1.0
        val weightedMean = items.sumOf { it.score * it.weight } / totalW
        val strongest = items.maxOf { it.score }
        return (0.6 * weightedMean + 0.4 * strongest)
    }

    private fun primaryThreatOf(present: Map<ScoreComponent, Double>): String? {
        val ranked = present.entries.sortedByDescending { it.value * weights.getValue(it.key) }
        val (comp, score) = ranked.first()
        if (score < 0.35) return null
        return when (comp) {
            ScoreComponent.AI -> "AI-Generated / Synthetic Media"
            ScoreComponent.PHISHING -> "Phishing / Financial Scam"
            ScoreComponent.SOURCE -> "Untrusted Source"
            ScoreComponent.AUTHENTICITY -> "Unverified Authenticity"
            ScoreComponent.METADATA -> "Metadata / Provenance Anomaly"
        }
    }

    private fun confidenceOf(present: Map<ScoreComponent, Double>, nSignals: Int): Double {
        val coverage = present.size.toDouble() / weights.size
        val decisiveness = present.values.sumOf { abs(it - 0.5) * 2 } / present.size
        val signalBonus = min(nSignals / 12.0, 1.0)
        return (0.45 * coverage + 0.40 * decisiveness + 0.15 * signalBonus).coerceIn(0.1, 0.99)
    }

    // ---- helpers ----
    private fun registeredDomain(url: String): String {
        val host = url.replace(Regex("^\\w+://"), "").substringBefore('/').substringBefore('?').lowercase()
        val parts = host.split('.')
        return if (parts.size >= 2) parts.takeLast(2).joinToString(".") else host
    }

    private fun levenshtein(a: String, b: String): Int {
        if (a == b) return 0
        if (a.isEmpty()) return b.length
        if (b.isEmpty()) return a.length
        var prev = IntArray(b.length + 1) { it }
        for (i in 1..a.length) {
            val cur = IntArray(b.length + 1)
            cur[0] = i
            for (j in 1..b.length) {
                val cost = if (a[i - 1] == b[j - 1]) 0 else 1
                cur[j] = minOf(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost)
            }
            prev = cur
        }
        return prev[b.length]
    }
}
