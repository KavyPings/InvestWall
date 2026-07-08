package com.investwall.app.share

import android.net.Uri
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.investwall.app.data.repository.AnalysisRepository
import com.investwall.app.domain.VerdictChange
import com.investwall.app.domain.model.TrustReport
import com.investwall.app.ui.UiState
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import java.io.IOException
import javax.inject.Inject

/** Drives analysis for content shared into the app via Android Share Intent. */
@HiltViewModel
class ShareViewModel @Inject constructor(
    private val repository: AnalysisRepository,
) : ViewModel() {

    private val _state = MutableStateFlow<UiState<TrustReport>>(UiState.Loading)
    val state: StateFlow<UiState<TrustReport>> = _state.asStateFlow()

    private var started = false

    fun analyzeText(text: String, source: String?) {
        if (started) return
        started = true
        // Instant on-device result first, then automatically (no button)
        // escalate to the backend's trained model and refine the result if
        // it changes meaningfully — matches the SMS auto-escalation flow.
        viewModelScope.launch {
            _state.value = UiState.Loading
            val localReport = try {
                repository.analyzeTextLocally(text, source ?: "shared")
            } catch (e: Exception) {
                _state.value = UiState.Error(e.message ?: "Analysis failed.")
                return@launch
            }
            _state.value = UiState.Success(localReport)

            try {
                val serverReport = repository.deepCheck(localReport)
                if (VerdictChange.isMeaningfulChange(localReport, serverReport)) {
                    _state.value = UiState.Success(serverReport)
                }
            } catch (e: IOException) {
                // Backend unreachable — keep showing the on-device result.
            } catch (e: Exception) {
                // Escalation failed for another reason — keep the on-device result.
            }
        }
    }

    fun analyzeUri(uri: Uri, source: String?) {
        if (started) return
        started = true
        analyze { repository.analyzeFile(uri, source ?: "shared") }
    }

    private fun analyze(block: suspend () -> TrustReport) {
        _state.value = UiState.Loading
        viewModelScope.launch {
            _state.value = try {
                UiState.Success(block())
            } catch (e: IOException) {
                UiState.Error("Can't reach the InvestWall backend. Open the app → Settings to set the server URL.")
            } catch (e: Exception) {
                UiState.Error(e.message ?: "Analysis failed.")
            }
        }
    }
}
