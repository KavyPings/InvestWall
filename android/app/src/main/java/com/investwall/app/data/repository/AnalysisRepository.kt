package com.investwall.app.data.repository

import android.content.ContentResolver
import android.net.Uri
import android.provider.OpenableColumns
import com.investwall.app.data.local.ReportDao
import com.investwall.app.data.remote.InvestWallApi
import com.investwall.app.data.remote.dto.AnalyzeTextRequest
import com.investwall.app.data.toDomain
import com.investwall.app.data.toEntity
import com.investwall.app.domain.model.TrustReport
import com.investwall.app.local.LocalAnalyzer
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody
import okhttp3.RequestBody.Companion.toRequestBody
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Single source of truth for analyses (MVVM Repository layer). Talks to the
 * FastAPI backend and mirrors every result into the Room cache.
 */
@Singleton
class AnalysisRepository @Inject constructor(
    private val api: InvestWallApi,
    private val dao: ReportDao,
    private val contentResolver: ContentResolver,
) {
    val recentReports: Flow<List<TrustReport>> =
        dao.observeRecent().map { list -> list.map { it.toDomain() } }

    val highRiskCount: Flow<Int> = dao.observeHighRiskCount()
    val totalCount: Flow<Int> = dao.observeTotalCount()

    /**
     * On-device analysis (privacy-first default for text/SMS): rules run locally,
     * nothing leaves the phone. Cached like any other report.
     */
    suspend fun analyzeTextLocally(text: String, source: String?, sender: String? = null): TrustReport =
        withContext(Dispatchers.Default) {
            val report = LocalAnalyzer.analyze(text, source, sender)
            dao.upsert(report.toEntity())
            report
        }

    /** Server-side analysis (full engines + optional ML). Content leaves the device. */
    suspend fun analyzeText(text: String, source: String?, sender: String? = null): TrustReport =
        withContext(Dispatchers.IO) {
            val dto = api.analyzeText(AnalyzeTextRequest(text = text, source = source, sender = sender))
            val entity = dto.toEntity()
            dao.upsert(entity)
            entity.toDomain()
        }

    /**
     * Escalate a locally-produced report to the server for a deep ML check.
     * Re-sends the original text, then removes the superseded local entry.
     */
    suspend fun deepCheck(local: TrustReport): TrustReport = withContext(Dispatchers.IO) {
        val text = local.inputPreview.orEmpty()
        require(text.isNotBlank()) { "No text available to re-check" }
        val server = analyzeText(text, local.source, local.sender)
        if (local.id != server.id) dao.deleteById(local.id)
        server
    }

    suspend fun analyzeFile(uri: Uri, source: String?, sender: String? = null): TrustReport =
        withContext(Dispatchers.IO) {
            val (bytes, name, mime) = readUri(uri)
            val body: RequestBody = bytes.toRequestBody(mime.toMediaTypeOrNull())
            val part = MultipartBody.Part.createFormData("file", name, body)
            val srcPart = source?.toRequestBody("text/plain".toMediaTypeOrNull())
            val senderPart = sender?.toRequestBody("text/plain".toMediaTypeOrNull())
            val dto = api.analyzeFile(part, srcPart, senderPart)
            val entity = dto.toEntity()
            dao.upsert(entity)
            entity.toDomain()
        }

    suspend fun getReport(id: String): TrustReport? = withContext(Dispatchers.IO) {
        dao.findById(id)?.toDomain() ?: runCatching {
            api.report(id).toEntity().also { dao.upsert(it) }.toDomain()
        }.getOrNull()
    }

    suspend fun refreshHistory() = withContext(Dispatchers.IO) {
        runCatching {
            // Pull server-side reports (e.g. SMS-triggered ones) into the cache.
            api.history(limit = 100).forEach { item ->
                if (dao.findById(item.id) == null) {
                    runCatching { api.report(item.id) }.getOrNull()?.let { dao.upsert(it.toEntity()) }
                }
            }
        }
    }

    suspend fun clearHistory() = withContext(Dispatchers.IO) { dao.clear() }

    /** Ping the backend; returns a short status string or an error. */
    suspend fun checkBackend(): Result<String> = withContext(Dispatchers.IO) {
        runCatching {
            val h = api.health()
            "${h.app} v${h.version} · LLM: ${h.llmProvider} · DB: ${h.database}"
        }
    }

    private data class FilePayload(val bytes: ByteArray, val name: String, val mime: String)

    private fun readUri(uri: Uri): FilePayload {
        val mime = contentResolver.getType(uri) ?: "application/octet-stream"
        var name = "upload"
        contentResolver.query(uri, null, null, null, null)?.use { c ->
            val idx = c.getColumnIndex(OpenableColumns.DISPLAY_NAME)
            if (idx >= 0 && c.moveToFirst()) name = c.getString(idx) ?: name
        }
        val bytes = contentResolver.openInputStream(uri)?.use { it.readBytes() }
            ?: throw IllegalStateException("Cannot read shared file")
        return FilePayload(bytes, name, mime)
    }
}
