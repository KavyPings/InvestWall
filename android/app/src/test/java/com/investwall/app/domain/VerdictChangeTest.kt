package com.investwall.app.domain

import com.investwall.app.domain.model.TrustBand
import com.investwall.app.domain.model.TrustReport
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class VerdictChangeTest {

    private fun report(score: Int, band: TrustBand) = TrustReport(
        id = "1", createdAt = 0L, modality = "text", source = "sms", sender = null,
        filename = null, inputPreview = "text", trustScore = score, band = band,
        confidence = 0.5f, primaryThreat = null, componentScores = emptyMap(),
        explanation = "", llmProvider = "template", evidence = emptyList(),
    )

    @Test
    fun `band change is meaningful`() {
        val local = report(60, TrustBand.POTENTIALLY_MANIPULATED)
        val server = report(20, TrustBand.HIGH_RISK)
        assertTrue(VerdictChange.isMeaningfulChange(local, server))
    }

    @Test
    fun `large score swing within the same band is meaningful`() {
        val local = report(85, TrustBand.HIGHLY_AUTHENTIC)
        val server = report(68, TrustBand.HIGHLY_AUTHENTIC)
        assertTrue(VerdictChange.isMeaningfulChange(local, server))
    }

    @Test
    fun `small score change is not meaningful`() {
        val local = report(85, TrustBand.HIGHLY_AUTHENTIC)
        val server = report(80, TrustBand.HIGHLY_AUTHENTIC)
        assertFalse(VerdictChange.isMeaningfulChange(local, server))
    }
}
