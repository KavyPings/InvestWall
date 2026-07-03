package com.investwall.app.ui.theme

import androidx.compose.material3.Typography
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp

/**
 * Typography using the platform default (Roboto). No decorative fonts — clean
 * and readable for non-technical users.
 */
private val Default = FontFamily.Default

val AppTypography = Typography(
    headlineMedium = TextStyle(
        fontFamily = Default, fontWeight = FontWeight.SemiBold,
        fontSize = 26.sp, lineHeight = 32.sp,
    ),
    headlineSmall = TextStyle(
        fontFamily = Default, fontWeight = FontWeight.SemiBold,
        fontSize = 22.sp, lineHeight = 28.sp,
    ),
    titleLarge = TextStyle(
        fontFamily = Default, fontWeight = FontWeight.SemiBold,
        fontSize = 18.sp, lineHeight = 24.sp,
    ),
    titleMedium = TextStyle(
        fontFamily = Default, fontWeight = FontWeight.Medium,
        fontSize = 16.sp, lineHeight = 22.sp,
    ),
    bodyLarge = TextStyle(
        fontFamily = Default, fontWeight = FontWeight.Normal,
        fontSize = 15.sp, lineHeight = 22.sp,
    ),
    bodyMedium = TextStyle(
        fontFamily = Default, fontWeight = FontWeight.Normal,
        fontSize = 14.sp, lineHeight = 20.sp,
    ),
    labelLarge = TextStyle(
        fontFamily = Default, fontWeight = FontWeight.Medium,
        fontSize = 14.sp, lineHeight = 18.sp,
    ),
    labelSmall = TextStyle(
        fontFamily = Default, fontWeight = FontWeight.Medium,
        fontSize = 12.sp, lineHeight = 16.sp,
    ),
)
