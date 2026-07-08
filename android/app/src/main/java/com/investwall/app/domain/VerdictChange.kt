package com.investwall.app.domain

import com.investwall.app.domain.model.TrustReport
import kotlin.math.abs

/**
 * Decides whether an automatic backend re-check (deep AI check) produced a
 * result different enough from the on-device result to be worth surfacing
 * again (updated notification / updated UI state).
 */
object VerdictChange {
    private const val MEANINGFUL_SCORE_DELTA = 15

    fun isMeaningfulChange(local: TrustReport, server: TrustReport): Boolean {
        if (local.band != server.band) return true
        return abs(local.trustScore - server.trustScore) >= MEANINGFUL_SCORE_DELTA
    }
}
