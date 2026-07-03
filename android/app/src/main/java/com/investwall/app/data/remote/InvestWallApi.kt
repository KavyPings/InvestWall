package com.investwall.app.data.remote

import com.investwall.app.data.remote.dto.AnalyzeTextRequest
import com.investwall.app.data.remote.dto.HealthDto
import com.investwall.app.data.remote.dto.HistoryItemDto
import com.investwall.app.data.remote.dto.TrustReportDto
import okhttp3.MultipartBody
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Multipart
import retrofit2.http.POST
import retrofit2.http.Part
import retrofit2.http.Path
import retrofit2.http.Query

/** Retrofit interface for the InvestWall backend. */
interface InvestWallApi {

    @GET("health")
    suspend fun health(): HealthDto

    @POST("analyze")
    suspend fun analyzeText(@Body req: AnalyzeTextRequest): TrustReportDto

    @Multipart
    @POST("analyze/file")
    suspend fun analyzeFile(
        @Part file: MultipartBody.Part,
        @Part("source") source: okhttp3.RequestBody?,
        @Part("sender") sender: okhttp3.RequestBody?,
    ): TrustReportDto

    @GET("history")
    suspend fun history(
        @Query("limit") limit: Int = 50,
        @Query("offset") offset: Int = 0,
    ): List<HistoryItemDto>

    @GET("report/{id}")
    suspend fun report(@Path("id") id: String): TrustReportDto
}
