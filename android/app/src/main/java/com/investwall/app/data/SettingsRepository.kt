package com.investwall.app.data

import android.content.Context
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import com.investwall.app.BuildConfig
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import javax.inject.Inject
import javax.inject.Singleton

private val Context.dataStore by preferencesDataStore(name = "investwall_settings")

/** User preferences (tech-stack §3 Room/local prefs). Backed by DataStore. */
@Singleton
class SettingsRepository @Inject constructor(
    @ApplicationContext private val context: Context,
) {
    private val backendUrlKey = stringPreferencesKey("backend_url")
    private val smsScanKey = booleanPreferencesKey("sms_scan_enabled")
    private val connectedEmailKey = stringPreferencesKey("connected_email")

    val backendUrl: Flow<String> = context.dataStore.data.map {
        it[backendUrlKey]?.takeIf { url -> url.isNotBlank() } ?: BuildConfig.BACKEND_URL
    }
    val smsScanEnabled: Flow<Boolean> = context.dataStore.data.map { it[smsScanKey] ?: false }
    val connectedEmail: Flow<String?> = context.dataStore.data.map { it[connectedEmailKey] }

    suspend fun setBackendUrl(url: String) =
        context.dataStore.edit { it[backendUrlKey] = url.trim() }

    suspend fun setSmsScanEnabled(enabled: Boolean) =
        context.dataStore.edit { it[smsScanKey] = enabled }

    suspend fun setConnectedEmail(email: String?) =
        context.dataStore.edit {
            if (email == null) it.remove(connectedEmailKey) else it[connectedEmailKey] = email
        }
}
