package com.investwall.app.ui.screens.report

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.text.selection.SelectionContainer
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Description
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.investwall.app.domain.model.ScoreComponent
import com.investwall.app.domain.model.TrustReport
import com.investwall.app.ui.UiState
import com.investwall.app.ui.components.AppTopBar
import com.investwall.app.ui.components.ComponentBar
import com.investwall.app.ui.components.EvidenceRow
import com.investwall.app.ui.components.SectionCard
import com.investwall.app.ui.components.StatusPill
import com.investwall.app.ui.components.componentLabel
import com.investwall.app.ui.components.tagline
import com.investwall.app.ui.components.visual
import com.investwall.app.ui.theme.Accent
import com.investwall.app.ui.theme.Border
import com.investwall.app.ui.theme.TextMuted
import com.investwall.app.ui.theme.TextPrimary
import com.investwall.app.ui.theme.TextSecondary
import com.investwall.app.ui.components.TrustScoreRing

@Composable
fun ReportScreen(
    onBack: () -> Unit,
    viewModel: ReportViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    Column(Modifier.fillMaxSize()) {
        AppTopBar(title = "Trust Report", onBack = onBack)
        when (val s = state) {
            is UiState.Loading -> Box(Modifier.fillMaxSize(), Alignment.Center) {
                CircularProgressIndicator(color = Accent, strokeWidth = 2.dp)
            }
            is UiState.Error -> Box(Modifier.fillMaxSize(), Alignment.Center) {
                Text(s.message, color = TextSecondary)
            }
            is UiState.Success -> ReportContent(s.data)
            else -> Unit
        }
    }
}

@Composable
private fun ReportContent(report: TrustReport) {
    val visual = report.band.visual()
    LazyColumn(
        Modifier.fillMaxWidth(),
        contentPadding = androidx.compose.foundation.layout.PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        // Score header
        item {
            SectionCard {
                Column(Modifier.fillMaxWidth(), horizontalAlignment = Alignment.CenterHorizontally) {
                    Spacer(Modifier.height(4.dp))
                    TrustScoreRing(score = report.trustScore, band = report.band)
                    Spacer(Modifier.height(16.dp))
                    StatusPill(text = report.band.label, color = visual.color)
                    Spacer(Modifier.height(10.dp))
                    Text(
                        report.band.tagline(),
                        color = TextSecondary,
                        style = MaterialTheme.typography.bodyMedium,
                    )
                    Spacer(Modifier.height(4.dp))
                    Text(
                        "Confidence ${(report.confidence * 100).toInt()}%  •  ${report.modality.replaceFirstChar { it.uppercase() }}",
                        color = TextMuted,
                        style = MaterialTheme.typography.labelSmall,
                    )
                }
            }
        }

        report.primaryThreat?.let { threat ->
            item {
                SectionCard {
                    Text("Primary concern", color = TextMuted, style = MaterialTheme.typography.labelSmall)
                    Spacer(Modifier.height(4.dp))
                    Text(threat, color = visual.color, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                }
            }
        }

        // Explanation
        item {
            SectionCard {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(Icons.Outlined.Description, contentDescription = null, tint = Accent)
                    Spacer(Modifier.height(0.dp))
                    Text("  Explanation", color = TextPrimary, style = MaterialTheme.typography.titleMedium)
                }
                Spacer(Modifier.height(10.dp))
                SelectionContainer {
                    Text(report.explanation, color = TextPrimary, style = MaterialTheme.typography.bodyLarge)
                }
            }
        }

        // Component breakdown
        if (report.componentScores.isNotEmpty()) {
            item {
                SectionCard {
                    Text("Score breakdown", color = TextPrimary, style = MaterialTheme.typography.titleMedium)
                    Spacer(Modifier.height(8.dp))
                    // Show components in a stable, meaningful order.
                    ScoreComponent.entries.forEach { comp ->
                        report.componentScores[comp.key]?.let { score ->
                            ComponentBar(label = comp.label, score = score)
                        }
                    }
                    // Any components not in the enum (future-proofing).
                    report.componentScores.filterKeys { key ->
                        ScoreComponent.fromKey(key) == null
                    }.forEach { (key, score) ->
                        ComponentBar(label = componentLabel(key), score = score)
                    }
                }
            }
        }

        // Evidence
        if (report.evidence.isNotEmpty()) {
            item {
                SectionCard {
                    Text("Evidence", color = TextPrimary, style = MaterialTheme.typography.titleMedium)
                    Spacer(Modifier.height(4.dp))
                    report.evidence.forEachIndexed { i, e ->
                        if (i > 0) HorizontalDivider(color = Border)
                        EvidenceRow(reason = e.reason, score = e.score)
                    }
                }
            }
        }

        item {
            Text(
                "Explanation generated by the ${report.llmProvider} reasoner over structured detector evidence.",
                color = TextMuted,
                style = MaterialTheme.typography.labelSmall,
                modifier = Modifier.padding(horizontal = 4.dp),
            )
        }
    }
}
