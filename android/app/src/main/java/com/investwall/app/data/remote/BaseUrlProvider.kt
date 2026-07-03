package com.investwall.app.data.remote

import com.investwall.app.BuildConfig
import okhttp3.HttpUrl.Companion.toHttpUrlOrNull
import okhttp3.Interceptor
import okhttp3.Response
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Holds the current backend base URL and rewrites each request's host/port to
 * match. This lets the Settings screen point the app at a different backend
 * (e.g. a LAN IP or deployed server) without rebuilding.
 */
@Singleton
class BaseUrlProvider @Inject constructor() : Interceptor {

    @Volatile
    private var baseUrl: String = BuildConfig.BACKEND_URL

    fun update(url: String) {
        val normalized = url.trim().let { if (it.endsWith("/")) it else "$it/" }
        if (normalized.toHttpUrlOrNull() != null) baseUrl = normalized
    }

    override fun intercept(chain: Interceptor.Chain): Response {
        val target = baseUrl.toHttpUrlOrNull() ?: return chain.proceed(chain.request())
        val request = chain.request()
        val newUrl = request.url.newBuilder()
            .scheme(target.scheme)
            .host(target.host)
            .port(target.port)
            .build()
        return chain.proceed(request.newBuilder().url(newUrl).build())
    }
}
