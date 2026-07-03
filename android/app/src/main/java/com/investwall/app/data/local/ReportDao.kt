package com.investwall.app.data.local

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import kotlinx.coroutines.flow.Flow

@Dao
interface ReportDao {

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsert(report: ReportEntity)

    @Query("SELECT * FROM reports ORDER BY createdAt DESC LIMIT :limit")
    fun observeRecent(limit: Int = 100): Flow<List<ReportEntity>>

    @Query("SELECT * FROM reports WHERE id = :id LIMIT 1")
    suspend fun findById(id: String): ReportEntity?

    @Query("SELECT COUNT(*) FROM reports WHERE trustScore < 40")
    fun observeHighRiskCount(): Flow<Int>

    @Query("SELECT COUNT(*) FROM reports")
    fun observeTotalCount(): Flow<Int>

    @Query("DELETE FROM reports")
    suspend fun clear()
}
