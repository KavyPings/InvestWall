package com.investwall.app.data.local

import androidx.room.Database
import androidx.room.RoomDatabase
import androidx.room.TypeConverters

@Database(entities = [ReportEntity::class], version = 1, exportSchema = false)
@TypeConverters(Converters::class)
abstract class InvestWallDatabase : RoomDatabase() {
    abstract fun reportDao(): ReportDao
}
