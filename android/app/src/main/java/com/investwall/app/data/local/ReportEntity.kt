package com.investwall.app.data.local

import androidx.room.Entity
import androidx.room.PrimaryKey
import androidx.room.TypeConverter
import kotlinx.serialization.decodeFromString
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json

/**
 * Cached analysis report (tech-stack §3 Room). Lets the user revisit previous
 * analyses without another network call. The full evidence/scores are stored as
 * JSON blobs for simplicity.
 */
@Entity(tableName = "reports")
data class ReportEntity(
    @PrimaryKey val id: String,
    val createdAt: Long,
    val modality: String,
    val source: String?,
    val sender: String?,
    val filename: String?,
    val inputPreview: String?,
    val trustScore: Int,
    val band: String,
    val bandLabel: String,
    val confidence: Float,
    val primaryThreat: String?,
    val componentScoresJson: String,
    val explanation: String,
    val llmProvider: String,
    val evidenceJson: String,
)

/** JSON converters for the map column. */
class Converters {
    private val json = Json { ignoreUnknownKeys = true }

    @TypeConverter
    fun mapToJson(map: Map<String, Float>): String = json.encodeToString(map)

    @TypeConverter
    fun jsonToMap(value: String): Map<String, Float> =
        if (value.isBlank()) emptyMap() else json.decodeFromString(value)
}
