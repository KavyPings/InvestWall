package com.investwall.app.sms

import android.content.Context
import androidx.hilt.work.HiltWorker
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.investwall.app.data.SettingsRepository
import com.investwall.app.data.repository.AnalysisRepository
import com.investwall.app.notifications.Notifier
import dagger.assisted.Assisted
import dagger.assisted.AssistedInject
import kotlinx.coroutines.flow.first

/**
 * Analyses a received SMS in the background and raises a notification when the
 * result is risky. Respects the user's "scan incoming SMS" preference.
 */
@HiltWorker
class SmsAnalysisWorker @AssistedInject constructor(
    @Assisted appContext: Context,
    @Assisted params: WorkerParameters,
    private val repository: AnalysisRepository,
    private val settings: SettingsRepository,
    private val notifier: Notifier,
) : CoroutineWorker(appContext, params) {

    override suspend fun doWork(): Result {
        if (!settings.smsScanEnabled.first()) return Result.success()

        val body = inputData.getString(KEY_BODY) ?: return Result.success()
        val sender = inputData.getString(KEY_SENDER)

        return try {
            val report = repository.analyzeText(text = body, source = "sms", sender = sender)
            notifier.notifyResult(report, sender)
            Result.success()
        } catch (e: Exception) {
            // Transient network/backend issues — let WorkManager retry.
            Result.retry()
        }
    }

    companion object {
        const val KEY_BODY = "body"
        const val KEY_SENDER = "sender"
    }
}
