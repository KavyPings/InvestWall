package com.investwall.app.ui.theme

import androidx.compose.ui.graphics.Color

/**
 * Plain dark palette. Deliberately flat: no gradients, no glassmorphism, no
 * purple "AI" accents. One calm blue accent, restrained neutrals, and three
 * semantic colours for the Trust bands (matching the backend band_color values).
 */

// Neutrals — layered greys for a plain dark surface hierarchy.
val Background = Color(0xFF0F0F10)      // app background
val Surface = Color(0xFF17171A)         // cards / sheets
val SurfaceHigh = Color(0xFF1F1F23)     // pressed / elevated rows
val Border = Color(0xFF2A2A2E)          // hairline dividers / card outlines

val TextPrimary = Color(0xFFF4F4F5)
val TextSecondary = Color(0xFFA1A1AA)
val TextMuted = Color(0xFF6B6B73)

// Single accent — a steady, non-purple blue.
val Accent = Color(0xFF4F9CF9)
val AccentSubtle = Color(0xFF1B2A3F)   // accent-tinted fill for chips/selection

// Trust band semantics (align with backend trust_score.py).
val RiskRed = Color(0xFFE5484D)         // High Risk
val WarnAmber = Color(0xFFF0883E)       // Potentially Manipulated
val SafeGreen = Color(0xFF3DA35D)       // Highly Authentic
