package com.investwall.app.domain.model

/**
 * Domain model for a completed analysis — the UI renders this. Mirrors the
 * backend TrustReport contract (see backend/app/api/schemas.py).
 */
data class TrustReport(
    val id: String,
    val createdAt: Long,
    val modality: String,
    val source: String?,
    val sender: String?,
    val filename: String?,
    val inputPreview: String?,
    val trustScore: Int,
    val band: TrustBand,
    val confidence: Float,
    val primaryThreat: String?,
    val componentScores: Map<String, Float>,
    val explanation: String,
    val llmProvider: String,
    val evidence: List<EvidenceItem>,
)

data class EvidenceItem(
    val signal: String,
    val component: String,
    val score: Float,
    val reason: String,
)

/** Trust bands, aligned with backend trust_score.py thresholds. */
enum class TrustBand(val key: String, val label: String) {
    HIGH_RISK("high_risk", "High Risk"),
    POTENTIALLY_MANIPULATED("potentially_manipulated", "Potentially Manipulated"),
    HIGHLY_AUTHENTIC("highly_authentic", "Highly Authentic");

    companion object {
        fun fromKey(key: String?): TrustBand = entries.firstOrNull { it.key == key }
            ?: fromScore(50)

        fun fromScore(score: Int): TrustBand = when {
            score >= 75 -> HIGHLY_AUTHENTIC
            score >= 40 -> POTENTIALLY_MANIPULATED
            else -> HIGH_RISK
        }
    }
}

/** Fusion components (PRD §8) with display labels for the score breakdown. */
enum class ScoreComponent(val key: String, val label: String) {
    AI("ai", "AI / Synthetic"),
    PHISHING("phishing", "Phishing"),
    SOURCE("source", "Source"),
    AUTHENTICITY("authenticity", "Authenticity"),
    METADATA("metadata", "Metadata");

    companion object {
        fun fromKey(key: String): ScoreComponent? = entries.firstOrNull { it.key == key }
    }
}
