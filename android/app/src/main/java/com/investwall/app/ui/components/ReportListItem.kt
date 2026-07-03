package com.investwall.app.ui.components

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.investwall.app.domain.model.TrustReport
import com.investwall.app.ui.theme.Border
import com.investwall.app.ui.theme.Surface
import com.investwall.app.ui.theme.TextMuted
import com.investwall.app.ui.theme.TextPrimary
import com.investwall.app.ui.theme.TextSecondary
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

private val dateFmt = SimpleDateFormat("d MMM, h:mm a", Locale.getDefault())

@Composable
fun ReportListItem(
    report: TrustReport,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val visual = report.band.visual()
    Row(
        modifier = modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(12.dp))
            .background(Surface)
            .border(BorderStroke(1.dp, Border), RoundedCornerShape(12.dp))
            .clickable(onClick = onClick)
            .padding(14.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        // Score chip in the band colour.
        Box(
            Modifier
                .size(46.dp)
                .clip(RoundedCornerShape(10.dp))
                .background(visual.color.copy(alpha = 0.16f)),
            contentAlignment = Alignment.Center,
        ) {
            Text(
                "${report.trustScore}",
                color = visual.color,
                fontWeight = FontWeight.SemiBold,
                fontSize = 17.sp,
            )
        }
        Spacer(Modifier.width(14.dp))
        Column(Modifier.weight(1f)) {
            Text(
                text = report.inputPreview?.takeIf { it.isNotBlank() }
                    ?: "${report.modality.replaceFirstChar { it.uppercase() }} analysis",
                color = TextPrimary,
                style = MaterialTheme.typography.bodyLarge,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
            Spacer(Modifier.size(3.dp))
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(report.band.label, color = visual.color, style = MaterialTheme.typography.labelSmall)
                Text("  •  ", color = TextMuted, style = MaterialTheme.typography.labelSmall)
                Text(
                    report.source?.replaceFirstChar { it.uppercase() } ?: report.modality.replaceFirstChar { it.uppercase() },
                    color = TextSecondary,
                    style = MaterialTheme.typography.labelSmall,
                )
                Text("  •  ", color = TextMuted, style = MaterialTheme.typography.labelSmall)
                Text(
                    dateFmt.format(Date(report.createdAt)),
                    color = TextMuted,
                    style = MaterialTheme.typography.labelSmall,
                )
            }
        }
    }
}
