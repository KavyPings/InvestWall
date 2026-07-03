"""Trust Score bands (PRD §8).

Trust Score is 0..100 where **higher = more trustworthy/authentic**.
Bands are calibrated to the PRD examples: 92 -> Highly Authentic,
45 -> Potentially Manipulated, 15 -> High Risk.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Band:
    key: str
    label: str
    color: str          # hex hint for the Android UI
    min_score: int


BANDS: list[Band] = [
    Band("high_risk", "High Risk", "#E53935", 0),
    Band("potentially_manipulated", "Potentially Manipulated", "#FB8C00", 40),
    Band("highly_authentic", "Highly Authentic", "#43A047", 75),
]


def band_for(score: float) -> Band:
    chosen = BANDS[0]
    for band in BANDS:
        if score >= band.min_score:
            chosen = band
    return chosen
