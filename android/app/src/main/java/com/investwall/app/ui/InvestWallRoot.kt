package com.investwall.app.ui

import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationBarItemDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.navigation.NavDestination.Companion.hierarchy
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import androidx.navigation.NavType
import com.investwall.app.ui.screens.analyze.AnalyzeScreen
import com.investwall.app.ui.screens.dashboard.DashboardScreen
import com.investwall.app.ui.screens.history.HistoryScreen
import com.investwall.app.ui.screens.report.ReportScreen
import com.investwall.app.ui.screens.settings.SettingsScreen
import com.investwall.app.ui.theme.Accent
import com.investwall.app.ui.theme.Background
import com.investwall.app.ui.theme.Border
import com.investwall.app.ui.theme.Surface
import com.investwall.app.ui.theme.TextMuted
import com.investwall.app.ui.theme.TextPrimary

@Composable
fun InvestWallRoot() {
    val navController = rememberNavController()
    val backStack by navController.currentBackStackEntryAsState()
    val currentRoute = backStack?.destination?.route

    val showBottomBar = currentRoute in TopLevelDestination.entries.map { it.route }

    Scaffold(
        containerColor = Background,
        bottomBar = {
            if (showBottomBar) {
                NavigationBar(containerColor = Surface, contentColor = TextPrimary) {
                    TopLevelDestination.entries.forEach { dest ->
                        val selected = backStack?.destination?.hierarchy?.any {
                            it.route == dest.route
                        } == true
                        NavigationBarItem(
                            selected = selected,
                            onClick = {
                                navController.navigate(dest.route) {
                                    popUpTo(navController.graph.findStartDestination().id) {
                                        saveState = true
                                    }
                                    launchSingleTop = true
                                    restoreState = true
                                }
                            },
                            icon = { Icon(dest.icon, contentDescription = dest.label) },
                            label = { Text(dest.label, style = MaterialTheme.typography.labelSmall) },
                            colors = NavigationBarItemDefaults.colors(
                                selectedIconColor = Accent,
                                selectedTextColor = Accent,
                                indicatorColor = Border,
                                unselectedIconColor = TextMuted,
                                unselectedTextColor = TextMuted,
                            ),
                        )
                    }
                }
            }
        },
    ) { padding ->
        NavHost(
            navController = navController,
            startDestination = Routes.DASHBOARD,
            modifier = Modifier.padding(padding),
        ) {
            composable(Routes.DASHBOARD) {
                DashboardScreen(
                    onAnalyze = { navController.navigate(Routes.ANALYZE) },
                    onOpenReport = { navController.navigate(Routes.report(it)) },
                    onOpenHistory = { navController.navigate(Routes.HISTORY) },
                )
            }
            composable(Routes.ANALYZE) {
                AnalyzeScreen(
                    onBack = { navController.popBackStack() },
                    onResult = { id ->
                        navController.navigate(Routes.report(id)) {
                            popUpTo(Routes.DASHBOARD)
                        }
                    },
                )
            }
            composable(Routes.HISTORY) {
                HistoryScreen(onOpenReport = { navController.navigate(Routes.report(it)) })
            }
            composable(Routes.SETTINGS) { SettingsScreen() }
            composable(
                route = Routes.REPORT,
                arguments = listOf(navArgument("id") { type = NavType.StringType }),
            ) {
                ReportScreen(onBack = { navController.popBackStack() })
            }
        }
    }
}
