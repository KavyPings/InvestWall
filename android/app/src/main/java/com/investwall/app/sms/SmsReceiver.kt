package com.investwall.app.sms

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.provider.Telephony
import androidx.work.Data
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager

/**
 * Automatic SMS monitoring (PRD §5 / tech-stack §3). On receipt, the message is
 * reassembled and handed to a WorkManager job for backend analysis so no network
 * work happens on the broadcast thread.
 */
class SmsReceiver : BroadcastReceiver() {

    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != Telephony.Sms.Intents.SMS_RECEIVED_ACTION) return

        val messages = Telephony.Sms.Intents.getMessagesFromIntent(intent) ?: return
        if (messages.isEmpty()) return

        val sender = messages.first().displayOriginatingAddress ?: "unknown"
        val body = buildString { messages.forEach { append(it.displayMessageBody ?: "") } }
        if (body.isBlank()) return

        val work = OneTimeWorkRequestBuilder<SmsAnalysisWorker>()
            .setInputData(
                Data.Builder()
                    .putString(SmsAnalysisWorker.KEY_BODY, body)
                    .putString(SmsAnalysisWorker.KEY_SENDER, sender)
                    .build(),
            )
            .build()
        WorkManager.getInstance(context).enqueue(work)
    }
}
