package com.investwall.app.ui

import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.History
import androidx.compose.material.icons.outlined.Home
import androidx.compose.material.icons.outlined.Settings
import androidx.compose.ui.graphics.vector.ImageVector

/** Central route definitions. */
object Routes {
    const val DASHBOARD = "dashboard"
    const val ANALYZE = "analyze/{kind}"
    fun analyze(kind: String) = "analyze/$kind"
    const val HISTORY = "history"
    const val SETTINGS = "settings"
    const val REPORT = "report/{id}"
    fun report(id: String) = "report/$id"
}

enum class TopLevelDestination(
    val route: String,
    val label: String,
    val icon: ImageVector,
) {
    HOME(Routes.DASHBOARD, "Home", Icons.Outlined.Home),
    HISTORY(Routes.HISTORY, "History", Icons.Outlined.History),
    SETTINGS(Routes.SETTINGS, "Settings", Icons.Outlined.Settings),
}
