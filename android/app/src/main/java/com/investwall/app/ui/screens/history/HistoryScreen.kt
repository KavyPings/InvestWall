package com.investwall.app.ui.screens.history

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.DeleteOutline
import androidx.compose.material.icons.outlined.History
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.investwall.app.ui.components.EmptyState
import com.investwall.app.ui.components.ReportListItem
import com.investwall.app.ui.theme.TextMuted
import com.investwall.app.ui.theme.TextPrimary

@Composable
fun HistoryScreen(
    onOpenReport: (String) -> Unit,
    viewModel: HistoryViewModel = hiltViewModel(),
) {
    val reports by viewModel.reports.collectAsStateWithLifecycle()

    Column(Modifier.fillMaxSize()) {
        Row(
            Modifier
                .fillMaxWidth()
                .padding(start = 16.dp, end = 8.dp, top = 20.dp, bottom = 8.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text("History", color = TextPrimary, style = MaterialTheme.typography.headlineSmall)
            if (reports.isNotEmpty()) {
                IconButton(onClick = { viewModel.clear() }) {
                    Icon(Icons.Outlined.DeleteOutline, contentDescription = "Clear history", tint = TextMuted)
                }
            }
        }

        if (reports.isEmpty()) {
            Box(Modifier.fillMaxSize(), Alignment.Center) {
                EmptyState(
                    icon = Icons.Outlined.History,
                    title = "No analyses yet",
                    subtitle = "Analyzed messages and shared files will be listed here.",
                )
            }
        } else {
            LazyColumn(
                contentPadding = PaddingValues(16.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                items(reports, key = { it.id }) { report ->
                    ReportListItem(report = report, onClick = { onOpenReport(report.id) })
                }
            }
        }
    }
}
