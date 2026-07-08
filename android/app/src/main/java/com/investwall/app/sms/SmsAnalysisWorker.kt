package com.investwall.app.sms

import android.content.Context
import androidx.hilt.work.HiltWorker
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.investwall.app.data.SettingsRepository
import com.investwall.app.data.repository.AnalysisRepository
import com.investwall.app.domain.VerdictChange
import com.investwall.app.notifications.Notifier
import dagger.assisted.Assisted
import dagger.assisted.AssistedInject
import kotlinx.coroutines.flow.first

/**
 * Analyses a received SMS in the background and raises a notification when the
 * result is risky. Respects the user's "scan incoming SMS" preference.
 *
 * The on-device rule engine screens the message first so a notification can
 * fire instantly even offline; the backend's trained model is then called
 * automatically (no user action) to refine the verdict, and the notification
 * is updated in place if the refined result changes meaningfully.
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

        val localReport = try {
            val report = repository.analyzeTextLocally(text = body, source = "sms", sender = sender)
            val notificationKey = report.id.hashCode()
            notifier.notifyResult(report, sender, notificationKey)
            report to notificationKey
        } catch (e: Exception) {
            return Result.retry()
        }

        val (report, notificationKey) = localReport
        // Automatic backend escalation — no button, matches the product
        // requirement that every message is checked, not just ones the user
        // opts into. Failures here are swallowed rather than retried: the
        // local result + notification already succeeded, and repeatedly
        // retrying the whole worker would just re-run the local analysis
        // and hammer a possibly-down backend.
        try {
            val serverReport = repository.deepCheck(report)
            if (VerdictChange.isMeaningfulChange(report, serverReport)) {
                notifier.notifyResult(serverReport, sender, notificationKey)
            }
        } catch (e: Exception) {
            // Backend unreachable or escalation failed — fall back to the
            // on-device-only result, which the user has already seen.
        }

        return Result.success()
    }

    companion object {
        const val KEY_BODY = "body"
        const val KEY_SENDER = "sender"
    }
}
