package com.investwall.app.ui.screens.analyze

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.selection.SelectionContainer
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Search
import androidx.compose.material.icons.outlined.UploadFile
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.TextFieldValue
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.investwall.app.ui.AnalyzeKind
import com.investwall.app.ui.UiState
import com.investwall.app.ui.components.AppTopBar
import com.investwall.app.ui.components.PrimaryButton
import com.investwall.app.ui.theme.Accent
import com.investwall.app.ui.theme.Border
import com.investwall.app.ui.theme.RiskRed
import com.investwall.app.ui.theme.Surface
import com.investwall.app.ui.theme.TextMuted
import com.investwall.app.ui.theme.TextPrimary
import com.investwall.app.ui.theme.TextSecondary

@Composable
fun AnalyzeScreen(
    kind: AnalyzeKind,
    onBack: () -> Unit,
    onResult: (String) -> Unit,
    viewModel: AnalyzeViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    val filePicker = rememberLauncherForActivityResult(
        ActivityResultContracts.OpenDocument(),
    ) { uri -> if (uri != null) viewModel.analyzeFile(uri, source = kind.id) }

    LaunchedEffect(state) {
        val s = state
        if (s is UiState.Success) {
            onResult(s.data.id)
            viewModel.reset()
        }
    }

    val loading = state is UiState.Loading

    Column(Modifier.fillMaxWidth()) {
        AppTopBar(title = kind.title, onBack = onBack)
        Column(Modifier.padding(16.dp)) {
            Text(kind.subtitle, color = TextSecondary, style = MaterialTheme.typography.bodyMedium)
            Spacer(Modifier.height(16.dp))

            if (kind.isText) {
                TextSection(loading = loading, onAnalyze = viewModel::analyze)
            } else {
                FileSection(
                    kind = kind,
                    loading = loading,
                    onChoose = { filePicker.launch(kind.mimeTypes) },
                )
            }

            if (loading) {
                Spacer(Modifier.height(22.dp))
                Row(verticalAlignment = Alignment.CenterVertically) {
                    CircularProgressIndicator(color = Accent, strokeWidth = 2.dp, modifier = Modifier.size(18.dp))
                    Spacer(Modifier.width(12.dp))
                    Text(
                        if (kind.isText) "Checking on your device…" else "Running detection & fusion…",
                        color = TextSecondary,
                        style = MaterialTheme.typography.bodyMedium,
                    )
                }
            }

            (state as? UiState.Error)?.let { err ->
                Spacer(Modifier.height(18.dp))
                Column(
                    Modifier
                        .fillMaxWidth()
                        .border(1.dp, RiskRed.copy(alpha = 0.5f), RoundedCornerShape(12.dp))
                        .background(RiskRed.copy(alpha = 0.10f), RoundedCornerShape(12.dp))
                        .padding(14.dp),
                ) {
                    Text("Couldn't analyze", color = RiskRed, style = MaterialTheme.typography.titleMedium)
                    Spacer(Modifier.height(4.dp))
                    SelectionContainer {
                        Text(err.message, color = TextSecondary, style = MaterialTheme.typography.bodyMedium)
                    }
                }
            }
        }
    }
}

@Composable
private fun TextSection(loading: Boolean, onAnalyze: (String, String?) -> Unit) {
    var input by remember { mutableStateOf(TextFieldValue("")) }
    OutlinedTextField(
        value = input,
        onValueChange = { input = it },
        modifier = Modifier
            .fillMaxWidth()
            .heightIn(min = 160.dp),
        placeholder = { Text("e.g. \"SEBI approved guaranteed 40% returns…\"", color = TextMuted) },
        colors = OutlinedTextFieldDefaults.colors(
            focusedBorderColor = Accent,
            unfocusedBorderColor = Border,
            focusedContainerColor = Surface,
            unfocusedContainerColor = Surface,
            cursorColor = Accent,
            focusedTextColor = TextPrimary,
            unfocusedTextColor = TextPrimary,
        ),
        shape = RoundedCornerShape(12.dp),
    )
    Spacer(Modifier.height(16.dp))
    PrimaryButton(
        text = if (loading) "Analyzing…" else "Analyze",
        icon = Icons.Outlined.Search,
        enabled = input.text.isNotBlank() && !loading,
        onClick = { onAnalyze(input.text, "manual") },
        modifier = Modifier.fillMaxWidth(),
    )
}

@Composable
private fun FileSection(kind: AnalyzeKind, loading: Boolean, onChoose: () -> Unit) {
    PrimaryButton(
        text = kind.pickerLabel,
        icon = Icons.Outlined.UploadFile,
        enabled = !loading,
        onClick = onChoose,
        modifier = Modifier.fillMaxWidth(),
    )
    Spacer(Modifier.height(12.dp))
    Text(
        "Tip: you can also Share content from WhatsApp, your gallery, or any app into InvestWall.",
        color = TextMuted,
        style = MaterialTheme.typography.labelSmall,
    )
}
