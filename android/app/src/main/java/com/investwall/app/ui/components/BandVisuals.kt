package com.investwall.app.ui.components

import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.CheckCircle
import androidx.compose.material.icons.outlined.Error
import androidx.compose.material.icons.outlined.Warning
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import com.investwall.app.domain.model.ScoreComponent
import com.investwall.app.domain.model.TrustBand
import com.investwall.app.ui.theme.RiskRed
import com.investwall.app.ui.theme.SafeGreen
import com.investwall.app.ui.theme.WarnAmber

/** Central mapping of a Trust band to its (flat) colour and icon. */
data class BandVisual(val color: Color, val icon: ImageVector)

fun TrustBand.visual(): BandVisual = when (this) {
    TrustBand.HIGH_RISK -> BandVisual(RiskRed, Icons.Outlined.Error)
    TrustBand.POTENTIALLY_MANIPULATED -> BandVisual(WarnAmber, Icons.Outlined.Warning)
    TrustBand.HIGHLY_AUTHENTIC -> BandVisual(SafeGreen, Icons.Outlined.CheckCircle)
}

/** A short, plain-language one-liner per band. */
fun TrustBand.tagline(): String = when (this) {
    TrustBand.HIGH_RISK -> "Do not act on this without verifying"
    TrustBand.POTENTIALLY_MANIPULATED -> "Treat with caution and verify"
    TrustBand.HIGHLY_AUTHENTIC -> "No significant risk signals found"
}

/** Colour for a component risk value (0 clean .. 1 risky). */
fun componentColor(score: Float): Color = when {
    score >= 0.6f -> RiskRed
    score >= 0.35f -> WarnAmber
    else -> SafeGreen
}

fun componentLabel(key: String): String =
    ScoreComponent.fromKey(key)?.label ?: key.replaceFirstChar { it.uppercase() }
