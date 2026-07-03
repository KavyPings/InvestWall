package com.investwall.app.ui.screens.history

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.investwall.app.data.repository.AnalysisRepository
import com.investwall.app.domain.model.TrustReport
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class HistoryViewModel @Inject constructor(
    private val repository: AnalysisRepository,
) : ViewModel() {

    val reports: StateFlow<List<TrustReport>> = repository.recentReports
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    init { viewModelScope.launch { repository.refreshHistory() } }

    fun clear() = viewModelScope.launch { repository.clearHistory() }
}
