package com.investwall.app.ui.screens.dashboard

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.investwall.app.data.repository.AnalysisRepository
import com.investwall.app.domain.model.TrustReport
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import javax.inject.Inject

data class DashboardState(
    val recent: List<TrustReport> = emptyList(),
    val totalScanned: Int = 0,
    val threatsBlocked: Int = 0,
)

@HiltViewModel
class DashboardViewModel @Inject constructor(
    private val repository: AnalysisRepository,
) : ViewModel() {

    val state: StateFlow<DashboardState> = combine(
        repository.recentReports,
        repository.totalCount,
        repository.highRiskCount,
    ) { recent, total, threats ->
        DashboardState(recent = recent.take(5), totalScanned = total, threatsBlocked = threats)
    }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), DashboardState())

    init {
        // Pull any server-side (e.g. SMS-triggered) reports into the cache.
        viewModelScope.launch { repository.refreshHistory() }
    }
}
