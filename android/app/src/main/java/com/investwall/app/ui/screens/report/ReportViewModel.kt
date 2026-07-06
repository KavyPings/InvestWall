package com.investwall.app.ui.screens.report

import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.investwall.app.data.repository.AnalysisRepository
import com.investwall.app.domain.model.TrustReport
import com.investwall.app.ui.UiState
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import java.io.IOException
import javax.inject.Inject

@HiltViewModel
class ReportViewModel @Inject constructor(
    private val repository: AnalysisRepository,
    savedStateHandle: SavedStateHandle,
) : ViewModel() {

    private val reportId: String = savedStateHandle["id"] ?: ""

    private val _state = MutableStateFlow<UiState<TrustReport>>(UiState.Loading)
    val state: StateFlow<UiState<TrustReport>> = _state.asStateFlow()

    private val _deepChecking = MutableStateFlow(false)
    val deepChecking: StateFlow<Boolean> = _deepChecking.asStateFlow()

    private val _deepError = MutableStateFlow<String?>(null)
    val deepError: StateFlow<String?> = _deepError.asStateFlow()

    init { load() }

    private fun load() {
        viewModelScope.launch {
            val report = repository.getReport(reportId)
            _state.value = if (report != null) UiState.Success(report)
            else UiState.Error("Report not found")
        }
    }

    /** Escalate an on-device report to the server's full ML analysis. */
    fun deepCheck() {
        val current = (_state.value as? UiState.Success)?.data ?: return
        _deepError.value = null
        _deepChecking.value = true
        viewModelScope.launch {
            try {
                _state.value = UiState.Success(repository.deepCheck(current))
            } catch (e: IOException) {
                _deepError.value = "Can't reach the backend. Check the server URL in Settings."
            } catch (e: Exception) {
                _deepError.value = e.message ?: "Deep check failed."
            } finally {
                _deepChecking.value = false
            }
        }
    }

    fun clearDeepError() { _deepError.value = null }
}
