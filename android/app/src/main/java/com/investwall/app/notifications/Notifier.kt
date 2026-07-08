package com.investwall.app.notifications

import android.Manifest
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import com.investwall.app.MainActivity
import com.investwall.app.R
import com.investwall.app.domain.model.TrustBand
import com.investwall.app.domain.model.TrustReport
import dagger.hilt.android.qualifiers.ApplicationContext
import javax.inject.Inject
import javax.inject.Singleton

/** Posts local notifications for automatic (SMS) analyses that look risky. */
@Singleton
class Notifier @Inject constructor(
    @ApplicationContext private val context: Context,
) {
    init {
        val channel = NotificationChannel(
            CHANNEL_ID,
            "Fraud alerts",
            NotificationManager.IMPORTANCE_HIGH,
        ).apply { description = "Warnings about risky SMS and shared content" }
        context.getSystemService(NotificationManager::class.java)
            .createNotificationChannel(channel)
    }

    fun notifyResult(report: TrustReport, sender: String?, notificationKey: Int = report.id.hashCode()) {
        // Only alert when there is something to worry about.
        if (report.band == TrustBand.HIGHLY_AUTHENTIC) return
        if (ContextCompat.checkSelfPermission(context, Manifest.permission.POST_NOTIFICATIONS)
            != PackageManager.PERMISSION_GRANTED
        ) return

        val title = when (report.band) {
            TrustBand.HIGH_RISK -> "High-risk message detected"
            else -> "Potentially manipulated message"
        }
        val text = buildString {
            if (!sender.isNullOrBlank()) append("From $sender · ")
            append("Trust ${report.trustScore}/100. ")
            report.primaryThreat?.let { append(it) }
        }

        val openApp = PendingIntent.getActivity(
            context, 0,
            Intent(context, MainActivity::class.java)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT,
        )

        val notification = NotificationCompat.Builder(context, CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_launcher_foreground)
            .setContentTitle(title)
            .setContentText(text)
            .setStyle(NotificationCompat.BigTextStyle().bigText(report.explanation))
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setAutoCancel(true)
            .setContentIntent(openApp)
            .build()

        NotificationManagerCompat.from(context).notify(notificationKey, notification)
    }

    companion object {
        private const val CHANNEL_ID = "investwall_alerts"
    }
}
