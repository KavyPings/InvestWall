package com.investwall.app.data

import com.investwall.app.data.local.ReportEntity
import com.investwall.app.data.remote.dto.EvidenceItemDto
import com.investwall.app.data.remote.dto.TrustReportDto
import com.investwall.app.domain.model.EvidenceItem
import com.investwall.app.domain.model.TrustBand
import com.investwall.app.domain.model.TrustReport
import kotlinx.serialization.decodeFromString
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import java.time.Instant
import java.time.format.DateTimeFormatter

private val json = Json { ignoreUnknownKeys = true }

private fun parseTimestamp(iso: String?): Long =
    try {
        if (iso.isNullOrBlank()) System.currentTimeMillis()
        else Instant.from(DateTimeFormatter.ISO_DATE_TIME.parse(iso)).toEpochMilli()
    } catch (_: Exception) {
        System.currentTimeMillis()
    }

/** Backend DTO -> Room entity (for offline caching). */
fun TrustReportDto.toEntity(): ReportEntity = ReportEntity(
    id = id ?: java.util.UUID.randomUUID().toString().replace("-", ""),
    createdAt = parseTimestamp(createdAt),
    modality = modality,
    source = source,
    sender = sender,
    filename = filename,
    inputPreview = inputPreview,
    trustScore = trustScore,
    band = band,
    bandLabel = bandLabel,
    confidence = confidence,
    primaryThreat = primaryThreat,
    componentScoresJson = json.encodeToString(componentScores),
    explanation = explanation,
    llmProvider = llmProvider,
    evidenceJson = json.encodeToString(evidence),
)

/** Room entity -> domain model (for the UI). */
fun ReportEntity.toDomain(): TrustReport {
    val scores: Map<String, Float> = if (componentScoresJson.isBlank()) emptyMap()
    else json.decodeFromString(componentScoresJson)
    val evidence: List<EvidenceItem> = if (evidenceJson.isBlank()) emptyList()
    else json.decodeFromString<List<EvidenceItemDto>>(evidenceJson)
        .map { EvidenceItem(it.signal, it.component, it.score, it.reason) }

    return TrustReport(
        id = id,
        createdAt = createdAt,
        modality = modality,
        source = source,
        sender = sender,
        filename = filename,
        inputPreview = inputPreview,
        trustScore = trustScore,
        band = TrustBand.fromKey(band),
        confidence = confidence,
        primaryThreat = primaryThreat,
        componentScores = scores,
        explanation = explanation,
        llmProvider = llmProvider,
        evidence = evidence,
    )
}

/** Backend DTO -> domain (direct, for freshly returned analyses). */
fun TrustReportDto.toDomain(): TrustReport = toEntity().toDomain()

/** Domain -> Room entity (for caching on-device analyses). */
fun TrustReport.toEntity(): ReportEntity = ReportEntity(
    id = id,
    createdAt = createdAt,
    modality = modality,
    source = source,
    sender = sender,
    filename = filename,
    inputPreview = inputPreview,
    trustScore = trustScore,
    band = band.key,
    bandLabel = band.label,
    confidence = confidence,
    primaryThreat = primaryThreat,
    componentScoresJson = json.encodeToString(componentScores),
    explanation = explanation,
    llmProvider = llmProvider,
    evidenceJson = json.encodeToString(
        evidence.map { EvidenceItemDto(it.signal, it.component, it.score, it.reason) },
    ),
)
