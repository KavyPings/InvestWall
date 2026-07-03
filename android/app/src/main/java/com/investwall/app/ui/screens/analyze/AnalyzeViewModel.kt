package com.investwall.app.ui.screens.analyze

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
class AnalyzeViewModel @Inject constructor(
    private val repository: AnalysisRepository,
) : ViewModel() {

    private val _state = MutableStateFlow<UiState<TrustReport>>(UiState.Idle)
    val state: StateFlow<UiState<TrustReport>> = _state.asStateFlow()

    fun analyze(text: String, source: String? = "manual") {
        if (text.isBlank()) return
        _state.value = UiState.Loading
        viewModelScope.launch {
            _state.value = try {
                UiState.Success(repository.analyzeText(text.trim(), source))
            } catch (e: IOException) {
                UiState.Error("Can't reach the backend. Check the server URL in Settings.")
            } catch (e: Exception) {
                UiState.Error(e.message ?: "Analysis failed. Please try again.")
            }
        }
    }

    fun reset() { _state.value = UiState.Idle }
}
