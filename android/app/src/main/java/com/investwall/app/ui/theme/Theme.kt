package com.investwall.app.ui.theme

import android.app.Activity
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.SideEffect
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalView
import androidx.core.view.WindowCompat

/**
 * InvestWall is dark-only by design: a single, plain dark scheme. We intentionally
 * do not offer a light theme or dynamic (Material You) colours to keep the look
 * consistent and free of purple tints.
 */
private val DarkColors = darkColorScheme(
    primary = Accent,
    onPrimary = Background,
    secondary = Accent,
    onSecondary = Background,
    background = Background,
    onBackground = TextPrimary,
    surface = Surface,
    onSurface = TextPrimary,
    surfaceVariant = SurfaceHigh,
    onSurfaceVariant = TextSecondary,
    outline = Border,
    outlineVariant = Border,
    error = RiskRed,
    onError = TextPrimary,
)

@Composable
fun InvestWallTheme(
    @Suppress("UNUSED_PARAMETER") darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit,
) {
    val view = LocalView.current
    if (!view.isInEditMode) {
        SideEffect {
            val window = (view.context as Activity).window
            window.statusBarColor = Background.toArgb()
            window.navigationBarColor = Background.toArgb()
            val controller = WindowCompat.getInsetsController(window, view)
            controller.isAppearanceLightStatusBars = false
            controller.isAppearanceLightNavigationBars = false
        }
    }
    MaterialTheme(
        colorScheme = DarkColors,
        typography = AppTypography,
        content = content,
    )
}
