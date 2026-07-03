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
import javax.inject.Inject

@HiltViewModel
class ReportViewModel @Inject constructor(
    private val repository: AnalysisRepository,
    savedStateHandle: SavedStateHandle,
) : ViewModel() {

    private val reportId: String = savedStateHandle["id"] ?: ""

    private val _state = MutableStateFlow<UiState<TrustReport>>(UiState.Loading)
    val state: StateFlow<UiState<TrustReport>> = _state.asStateFlow()

    init { load() }

    private fun load() {
        viewModelScope.launch {
            val report = repository.getReport(reportId)
            _state.value = if (report != null) UiState.Success(report)
            else UiState.Error("Report not found")
        }
    }
}
