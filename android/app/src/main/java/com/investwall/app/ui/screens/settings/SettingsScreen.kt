package com.investwall.app.ui.screens.settings

import android.Manifest
import android.app.Activity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.MailOutline
import androidx.compose.material.icons.outlined.Sms
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.investwall.app.BuildConfig
import com.investwall.app.ui.components.SecondaryButton
import com.investwall.app.ui.components.SectionCard
import com.investwall.app.ui.theme.Accent
import com.investwall.app.ui.theme.Background
import com.investwall.app.ui.theme.Border
import com.investwall.app.ui.theme.RiskRed
import com.investwall.app.ui.theme.SafeGreen
import com.investwall.app.ui.theme.Surface
import com.investwall.app.ui.theme.TextMuted
import com.investwall.app.ui.theme.TextPrimary
import com.investwall.app.ui.theme.TextSecondary
import com.investwall.app.ui.screens.settings.gmail.rememberGmailConnector

@Composable
fun SettingsScreen(viewModel: SettingsViewModel = hiltViewModel()) {
    val backendUrl by viewModel.backendUrl.collectAsStateWithLifecycle()
    val smsEnabled by viewModel.smsScanEnabled.collectAsStateWithLifecycle()
    val connectedEmail by viewModel.connectedEmail.collectAsStateWithLifecycle()
    val status by viewModel.status.collectAsStateWithLifecycle()

    var urlField by remember(backendUrl) { mutableStateOf(backendUrl) }
    val context = LocalContext.current

    LaunchedEffect(Unit) { viewModel.checkBackend() }

    // SMS permission launcher.
    val smsPermissionLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission(),
    ) { granted -> viewModel.setSmsScan(granted) }

    // Gmail OAuth connector (scaffold — see gmail/GmailConnector.kt).
    val gmailConnector = rememberGmailConnector(
        onConnected = { email -> viewModel.setConnectedEmail(email) },
    )

    LazyColumn(
        Modifier.fillMaxWidth(),
        contentPadding = androidx.compose.foundation.layout.PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        item {
            Text(
                "Settings",
                color = TextPrimary,
                style = MaterialTheme.typography.headlineSmall,
                modifier = Modifier.padding(top = 8.dp, bottom = 4.dp),
            )
        }

        // Backend connection
        item {
            SectionCard {
                Text("Backend server", color = TextPrimary, style = MaterialTheme.typography.titleMedium)
                Spacer(Modifier.height(4.dp))
                Text(
                    "The InvestWall analysis API. Use 10.0.2.2 for an emulator, or your machine's LAN IP for a physical device.",
                    color = TextSecondary,
                    style = MaterialTheme.typography.bodyMedium,
                )
                Spacer(Modifier.height(12.dp))
                OutlinedTextField(
                    value = urlField,
                    onValueChange = { urlField = it },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                    label = { Text("Base URL") },
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedBorderColor = Accent,
                        unfocusedBorderColor = Border,
                        focusedContainerColor = Surface,
                        unfocusedContainerColor = Surface,
                        cursorColor = Accent,
                        focusedTextColor = TextPrimary,
                        unfocusedTextColor = TextPrimary,
                        focusedLabelColor = Accent,
                        unfocusedLabelColor = TextMuted,
                    ),
                    shape = RoundedCornerShape(12.dp),
                )
                Spacer(Modifier.height(12.dp))
                SecondaryButton(
                    text = "Save & test connection",
                    onClick = { viewModel.saveBackendUrl(urlField) },
                    modifier = Modifier.fillMaxWidth(),
                )
                Spacer(Modifier.height(10.dp))
                when (val s = status) {
                    is BackendStatus.Checking -> StatusLine("Checking…", TextSecondary)
                    is BackendStatus.Online -> StatusLine("Connected · ${s.info}", SafeGreen)
                    is BackendStatus.Offline -> StatusLine("Offline · ${s.message}", RiskRed)
                    BackendStatus.Unknown -> Unit
                }
            }
        }

        // Automatic protection
        item {
            SectionCard {
                Text("Automatic protection", color = TextPrimary, style = MaterialTheme.typography.titleMedium)
                Spacer(Modifier.height(8.dp))
                ToggleRow(
                    icon = Icons.Outlined.Sms,
                    title = "Scan incoming SMS",
                    subtitle = "Automatically checks new text messages for phishing and scams.",
                    checked = smsEnabled,
                    onCheckedChange = { want ->
                        if (want) smsPermissionLauncher.launch(Manifest.permission.RECEIVE_SMS)
                        else viewModel.setSmsScan(false)
                    },
                )
            }
        }

        // Email
        item {
            SectionCard {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    androidx.compose.material3.Icon(Icons.Outlined.MailOutline, null, tint = Accent)
                    Spacer(Modifier.height(0.dp))
                    Text("  Gmail", color = TextPrimary, style = MaterialTheme.typography.titleMedium)
                }
                Spacer(Modifier.height(6.dp))
                if (connectedEmail != null) {
                    Text("Connected as $connectedEmail", color = SafeGreen, style = MaterialTheme.typography.bodyMedium)
                    Spacer(Modifier.height(10.dp))
                    SecondaryButton(
                        text = "Disconnect",
                        onClick = { gmailConnector.disconnect(); viewModel.setConnectedEmail(null) },
                        modifier = Modifier.fillMaxWidth(),
                    )
                } else {
                    Text(
                        "Connect Gmail to let InvestWall scan incoming emails for phishing (read-only).",
                        color = TextSecondary,
                        style = MaterialTheme.typography.bodyMedium,
                    )
                    Spacer(Modifier.height(10.dp))
                    SecondaryButton(
                        text = "Connect Gmail",
                        onClick = { gmailConnector.connect() },
                        modifier = Modifier.fillMaxWidth(),
                    )
                }
            }
        }

        // About
        item {
            SectionCard {
                Text("About", color = TextPrimary, style = MaterialTheme.typography.titleMedium)
                Spacer(Modifier.height(6.dp))
                Text("InvestWall v${BuildConfig.VERSION_NAME}", color = TextSecondary, style = MaterialTheme.typography.bodyMedium)
                Text(
                    "AI-driven detection of synthetic media & phishing attacks for retail investors.",
                    color = TextMuted,
                    style = MaterialTheme.typography.bodyMedium,
                )
            }
        }
    }
}

@Composable
private fun StatusLine(text: String, color: androidx.compose.ui.graphics.Color) {
    Text(text, color = color, style = MaterialTheme.typography.labelLarge)
}

@Composable
private fun ToggleRow(
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    title: String,
    subtitle: String,
    checked: Boolean,
    onCheckedChange: (Boolean) -> Unit,
) {
    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
        androidx.compose.material3.Icon(icon, null, tint = Accent)
        Spacer(Modifier.height(0.dp))
        Column(Modifier.weight(1f).padding(start = 12.dp, end = 12.dp)) {
            Text(title, color = TextPrimary, style = MaterialTheme.typography.bodyLarge)
            Text(subtitle, color = TextSecondary, style = MaterialTheme.typography.bodyMedium)
        }
        Switch(
            checked = checked,
            onCheckedChange = onCheckedChange,
            colors = SwitchDefaults.colors(
                checkedThumbColor = Background,
                checkedTrackColor = Accent,
                uncheckedThumbColor = TextMuted,
                uncheckedTrackColor = Surface,
                uncheckedBorderColor = Border,
            ),
        )
    }
}
