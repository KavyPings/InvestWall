package com.investwall.app.local

import com.investwall.app.domain.model.EvidenceItem
import com.investwall.app.domain.model.TrustBand

/**
 * Deterministic, on-device explanation generator — a Kotlin port of the
 * backend's template explainer. Turns the fused evidence + band into plain,
 * actionable prose without any model or network call.
 */
object LocalExplainer {

    fun explain(
        band: TrustBand,
        trustScore: Int,
        confidence: Double,
        primaryThreat: String?,
        evidence: List<EvidenceItem>,
    ): String {
        val parts = mutableListOf<String>()

        val opener = when (band) {
            TrustBand.HIGH_RISK -> "This message is assessed as HIGH RISK."
            TrustBand.POTENTIALLY_MANIPULATED ->
                "This message is POTENTIALLY MANIPULATED — treat it with caution."
            TrustBand.HIGHLY_AUTHENTIC -> "This message appears HIGHLY AUTHENTIC."
        }
        parts += "$opener Trust Score: $trustScore/100 (${band.label}, " +
            "confidence ${(confidence * 100).toInt()}%)."

        if (primaryThreat != null) parts += "Primary concern: $primaryThreat."

        val reasons = evidence.filter { it.score >= 0.3f }
            .map { it.reason }.distinct().take(5)
        if (reasons.isNotEmpty()) {
            parts += "This was flagged because: " + reasons.joinToString(" ") { "• $it" }
        } else if (band == TrustBand.HIGHLY_AUTHENTIC) {
            parts += "No significant phishing or scam signals were found in this text."
        }

        parts += when (band) {
            TrustBand.HIGH_RISK ->
                "Recommendation: do NOT click links, share OTP/credentials, or transfer money. " +
                    "Independently verify through the official website or a known contact first."
            TrustBand.POTENTIALLY_MANIPULATED ->
                "Recommendation: verify the sender and any claims through an official channel before acting."
            TrustBand.HIGHLY_AUTHENTIC ->
                "You can proceed with normal caution, but always confirm major financial decisions " +
                    "through official sources."
        }
        return parts.joinToString(" ")
    }
}
