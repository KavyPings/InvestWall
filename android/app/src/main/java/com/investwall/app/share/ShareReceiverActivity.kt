package com.investwall.app.share

import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.viewModels
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.investwall.app.domain.model.TrustReport
import com.investwall.app.ui.UiState
import com.investwall.app.ui.components.AppTopBar
import com.investwall.app.ui.components.EvidenceRow
import com.investwall.app.ui.components.PrimaryButton
import com.investwall.app.ui.components.SectionCard
import com.investwall.app.ui.components.StatusPill
import com.investwall.app.ui.components.TrustScoreRing
import com.investwall.app.ui.components.tagline
import com.investwall.app.ui.components.visual
import com.investwall.app.ui.theme.Accent
import com.investwall.app.ui.theme.Background
import com.investwall.app.ui.theme.InvestWallTheme
import com.investwall.app.ui.theme.TextPrimary
import com.investwall.app.ui.theme.TextSecondary
import dagger.hilt.android.AndroidEntryPoint

/** Entry point for content shared from other apps (PRD §5 user-initiated). */
@AndroidEntryPoint
class ShareReceiverActivity : ComponentActivity() {

    private val viewModel: ShareViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        enableEdgeToEdge()
        super.onCreate(savedInstanceState)
        handleIntent(intent)

        setContent {
            InvestWallTheme {
                Surface(Modifier.fillMaxSize(), color = Background) {
                    val state by viewModel.state.collectAsStateWithLifecycle()
                    Column(Modifier.fillMaxSize()) {
                        AppTopBar(title = "InvestWall", onBack = { finish() })
                        when (val s = state) {
                            is UiState.Loading -> LoadingBox()
                            is UiState.Error -> Box(Modifier.fillMaxSize(), Alignment.Center) {
                                Text(s.message, color = TextSecondary, modifier = Modifier.padding(24.dp))
                            }
                            is UiState.Success -> ShareResult(s.data, onDone = { finish() })
                            else -> Unit
                        }
                    }
                }
            }
        }
    }

    private fun handleIntent(intent: Intent?) {
        if (intent?.action != Intent.ACTION_SEND) {
            if (intent?.action == Intent.ACTION_SEND_MULTIPLE) {
                firstStreamUri(intent)?.let { viewModel.analyzeUri(it, referrerSource()) }
            }
            return
        }
        val type = intent.type ?: ""
        val text = intent.getStringExtra(Intent.EXTRA_TEXT)
        val stream = streamUri(intent)
        when {
            stream != null -> viewModel.analyzeUri(stream, referrerSource())
            type.startsWith("text/") && !text.isNullOrBlank() ->
                viewModel.analyzeText(text, referrerSource())
            !text.isNullOrBlank() -> viewModel.analyzeText(text, referrerSource())
        }
    }

    @Suppress("DEPRECATION")
    private fun streamUri(intent: Intent): Uri? =
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU)
            intent.getParcelableExtra(Intent.EXTRA_STREAM, Uri::class.java)
        else intent.getParcelableExtra(Intent.EXTRA_STREAM)

    @Suppress("DEPRECATION")
    private fun firstStreamUri(intent: Intent): Uri? =
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU)
            intent.getParcelableArrayListExtra(Intent.EXTRA_STREAM, Uri::class.java)?.firstOrNull()
        else intent.getParcelableArrayListExtra<Uri>(Intent.EXTRA_STREAM)?.firstOrNull()

    /** Best-effort originating app label for the `source` field. */
    private fun referrerSource(): String? =
        referrer?.host?.substringAfterLast('.')?.takeIf { it.isNotBlank() } ?: "shared"
}

@Composable
private fun LoadingBox() {
    Box(Modifier.fillMaxSize(), Alignment.Center) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            CircularProgressIndicator(color = Accent, strokeWidth = 2.dp)
            Spacer(Modifier.height(16.dp))
            Text("Analyzing shared content…", color = TextSecondary)
        }
    }
}

@Composable
private fun ShareResult(report: TrustReport, onDone: () -> Unit) {
    val visual = report.band.visual()
    LazyColumn(
        Modifier.fillMaxWidth(),
        contentPadding = androidx.compose.foundation.layout.PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        item {
            SectionCard {
                Column(Modifier.fillMaxWidth(), horizontalAlignment = Alignment.CenterHorizontally) {
                    TrustScoreRing(score = report.trustScore, band = report.band)
                    Spacer(Modifier.height(14.dp))
                    StatusPill(text = report.band.label, color = visual.color)
                    Spacer(Modifier.height(10.dp))
                    Text(report.band.tagline(), color = TextSecondary, style = MaterialTheme.typography.bodyMedium)
                }
            }
        }
        item {
            SectionCard {
                Text("Why", color = TextPrimary, style = MaterialTheme.typography.titleMedium)
                Spacer(Modifier.height(8.dp))
                Text(report.explanation, color = TextPrimary, style = MaterialTheme.typography.bodyLarge)
            }
        }
        if (report.evidence.isNotEmpty()) {
            item {
                SectionCard {
                    Text("Top signals", color = TextPrimary, style = MaterialTheme.typography.titleMedium)
                    report.evidence.take(4).forEach { EvidenceRow(reason = it.reason, score = it.score) }
                }
            }
        }
        item {
            PrimaryButton(text = "Done", onClick = onDone, modifier = Modifier.fillMaxWidth())
        }
    }
}
