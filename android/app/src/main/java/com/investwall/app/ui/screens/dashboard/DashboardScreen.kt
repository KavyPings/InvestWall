package com.investwall.app.ui.screens.dashboard

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.outlined.Shield
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.investwall.app.ui.components.EmptyState
import com.investwall.app.ui.components.PrimaryButton
import com.investwall.app.ui.components.ReportListItem
import com.investwall.app.ui.components.SectionCard
import com.investwall.app.ui.theme.Accent
import com.investwall.app.ui.theme.RiskRed
import com.investwall.app.ui.theme.TextPrimary
import com.investwall.app.ui.theme.TextSecondary

@Composable
fun DashboardScreen(
    onAnalyze: () -> Unit,
    onOpenReport: (String) -> Unit,
    onOpenHistory: () -> Unit,
    viewModel: DashboardViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    LazyColumn(
        modifier = Modifier.fillMaxWidth(),
        contentPadding = androidx.compose.foundation.layout.PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        item {
            Column(Modifier.padding(top = 12.dp, bottom = 4.dp)) {
                Text("InvestWall", color = TextPrimary, fontSize = 26.sp, fontWeight = FontWeight.SemiBold)
                Text(
                    "Your AI trust layer against financial fraud",
                    color = TextSecondary,
                    style = MaterialTheme.typography.bodyMedium,
                )
            }
        }

        item {
            Row(horizontalArrangement = Arrangement.spacedBy(14.dp)) {
                StatCard(
                    modifier = Modifier.weight(1f),
                    value = "${state.totalScanned}",
                    label = "Items scanned",
                    color = Accent,
                )
                StatCard(
                    modifier = Modifier.weight(1f),
                    value = "${state.threatsBlocked}",
                    label = "High-risk flagged",
                    color = RiskRed,
                )
            }
        }

        item {
            SectionCard {
                Text("Check something now", color = TextPrimary, style = MaterialTheme.typography.titleMedium)
                Spacer(Modifier.height(6.dp))
                Text(
                    "Paste a message, or share content from any app into InvestWall to get a Trust Score.",
                    color = TextSecondary,
                    style = MaterialTheme.typography.bodyMedium,
                )
                Spacer(Modifier.height(14.dp))
                PrimaryButton(
                    text = "Analyze a message",
                    icon = Icons.Filled.Add,
                    onClick = onAnalyze,
                    modifier = Modifier.fillMaxWidth(),
                )
            }
        }

        item {
            Row(
                Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text("Recent", color = TextPrimary, style = MaterialTheme.typography.titleMedium)
                if (state.recent.isNotEmpty()) {
                    TextButton(onClick = onOpenHistory) { Text("See all", color = Accent) }
                }
            }
        }

        if (state.recent.isEmpty()) {
            item {
                SectionCard {
                    EmptyState(
                        icon = Icons.Outlined.Shield,
                        title = "Nothing analyzed yet",
                        subtitle = "Your recent Trust reports will appear here.",
                    )
                }
            }
        } else {
            items(state.recent, key = { it.id }) { report ->
                ReportListItem(report = report, onClick = { onOpenReport(report.id) })
            }
        }
    }
}

@Composable
private fun StatCard(value: String, label: String, color: androidx.compose.ui.graphics.Color, modifier: Modifier = Modifier) {
    SectionCard(modifier = modifier) {
        Text(value, color = color, fontSize = 28.sp, fontWeight = FontWeight.SemiBold)
        Text(label, color = TextSecondary, style = MaterialTheme.typography.bodyMedium)
    }
}
