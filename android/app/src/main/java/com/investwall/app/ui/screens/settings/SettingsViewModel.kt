package com.investwall.app.ui.screens.settings

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.investwall.app.data.SettingsRepository
import com.investwall.app.data.remote.BaseUrlProvider
import com.investwall.app.data.repository.AnalysisRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import javax.inject.Inject

sealed interface BackendStatus {
    data object Unknown : BackendStatus
    data object Checking : BackendStatus
    data class Online(val info: String) : BackendStatus
    data class Offline(val message: String) : BackendStatus
}

@HiltViewModel
class SettingsViewModel @Inject constructor(
    private val settings: SettingsRepository,
    private val analysisRepository: AnalysisRepository,
    private val baseUrlProvider: BaseUrlProvider,
) : ViewModel() {

    val backendUrl: StateFlow<String> = settings.backendUrl
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), "")
    val smsScanEnabled: StateFlow<Boolean> = settings.smsScanEnabled
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), false)
    val connectedEmail: StateFlow<String?> = settings.connectedEmail
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), null)

    private val _status = MutableStateFlow<BackendStatus>(BackendStatus.Unknown)
    val status: StateFlow<BackendStatus> = _status

    fun saveBackendUrl(url: String) {
        viewModelScope.launch {
            settings.setBackendUrl(url)
            baseUrlProvider.update(url)
            checkBackend()
        }
    }

    fun checkBackend() {
        _status.value = BackendStatus.Checking
        viewModelScope.launch {
            analysisRepository.checkBackend()
                .onSuccess { _status.value = BackendStatus.Online(it) }
                .onFailure { _status.value = BackendStatus.Offline(it.message ?: "Unreachable") }
        }
    }

    fun setSmsScan(enabled: Boolean) = viewModelScope.launch { settings.setSmsScanEnabled(enabled) }

    fun setConnectedEmail(email: String?) = viewModelScope.launch { settings.setConnectedEmail(email) }
}
