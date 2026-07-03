package com.investwall.app.di

import android.content.ContentResolver
import android.content.Context
import androidx.room.Room
import com.investwall.app.data.local.InvestWallDatabase
import com.investwall.app.data.local.ReportDao
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object AppModule {

    @Provides
    @Singleton
    fun provideDatabase(@ApplicationContext context: Context): InvestWallDatabase =
        Room.databaseBuilder(context, InvestWallDatabase::class.java, "investwall.db")
            .fallbackToDestructiveMigration()
            .build()

    @Provides
    fun provideReportDao(db: InvestWallDatabase): ReportDao = db.reportDao()

    @Provides
    fun provideContentResolver(@ApplicationContext context: Context): ContentResolver =
        context.contentResolver
}
