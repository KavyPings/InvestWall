package com.investwall.app.data.remote.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

/** Wire models matching the FastAPI backend JSON contract. */

@Serializable
data class AnalyzeTextRequest(
    val text: String,
    val source: String? = null,
    val sender: String? = null,
)

@Serializable
data class EvidenceItemDto(
    val signal: String,
    val component: String,
    val score: Float,
    val reason: String,
)

@Serializable
data class TrustReportDto(
    val id: String? = null,
    @SerialName("created_at") val createdAt: String? = null,
    val modality: String,
    val source: String? = null,
    val sender: String? = null,
    val filename: String? = null,
    @SerialName("input_preview") val inputPreview: String? = null,
    @SerialName("trust_score") val trustScore: Int,
    val band: String,
    @SerialName("band_label") val bandLabel: String,
    @SerialName("band_color") val bandColor: String? = null,
    val confidence: Float,
    @SerialName("primary_threat") val primaryThreat: String? = null,
    @SerialName("component_scores") val componentScores: Map<String, Float> = emptyMap(),
    val explanation: String,
    @SerialName("llm_provider") val llmProvider: String = "template",
    val evidence: List<EvidenceItemDto> = emptyList(),
)

@Serializable
data class HistoryItemDto(
    val id: String,
    @SerialName("created_at") val createdAt: String,
    val modality: String,
    val source: String? = null,
    @SerialName("trust_score") val trustScore: Int,
    val band: String,
    @SerialName("band_label") val bandLabel: String,
    @SerialName("primary_threat") val primaryThreat: String? = null,
    @SerialName("input_preview") val inputPreview: String? = null,
)

@Serializable
data class HealthDto(
    val status: String,
    val app: String,
    val version: String,
    @SerialName("llm_provider") val llmProvider: String,
    val features: Map<String, Boolean> = emptyMap(),
    val database: String,
)
