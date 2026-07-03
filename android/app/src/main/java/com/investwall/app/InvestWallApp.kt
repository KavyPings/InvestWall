package com.investwall.app

import android.app.Application
import androidx.hilt.work.HiltWorkerFactory
import androidx.work.Configuration
import com.investwall.app.data.SettingsRepository
import com.investwall.app.data.remote.BaseUrlProvider
import dagger.hilt.android.HiltAndroidApp
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltAndroidApp
class InvestWallApp : Application(), Configuration.Provider {

    @Inject lateinit var workerFactory: HiltWorkerFactory
    @Inject lateinit var settings: SettingsRepository
    @Inject lateinit var baseUrlProvider: BaseUrlProvider

    override val workManagerConfiguration: Configuration
        get() = Configuration.Builder()
            .setWorkerFactory(workerFactory)
            .build()

    override fun onCreate() {
        super.onCreate()
        // Apply any user-saved backend URL to the network layer at startup.
        CoroutineScope(Dispatchers.IO).launch {
            runCatching { baseUrlProvider.update(settings.backendUrl.first()) }
        }
    }
}
