"""Module 4 — Audio Analysis Engine (PRD §6).

Pipeline: decode -> spectral/MFCC heuristics -> learned deepfake/voice-clone
detector (AASIST/RawNet2-style spoof model) -> optional Whisper speech-to-text
-> transcript scam analysis (reuses TextEngine) -> LLM explanation.

The deepfake model + Whisper are flag-gated and lazy-loaded; the engine degrades
to the spectral heuristics if they're unavailable.
"""
from __future__ import annotations

import io
import logging

import numpy as np

from app.config import get_settings
from app.core.evidence import Component, EvidenceBundle, Modality
from app.engines.base import Engine, Payload

logger = logging.getLogger("investwall.engine.audio")

_WHISPER = None
_WHISPER_TRIED = False
_AUDIO_MODEL = None
_AUDIO_MODEL_TRIED = False

_FAKE_TOKENS = ("fake", "spoof", "synthetic", "clone", "generated", "deepfake", "ai")
_REAL_TOKENS = ("real", "bonafide", "genuine", "human", "authentic")


def _get_audio_model():
    global _AUDIO_MODEL, _AUDIO_MODEL_TRIED
    if _AUDIO_MODEL is not None or _AUDIO_MODEL_TRIED:
        return _AUDIO_MODEL
    _AUDIO_MODEL_TRIED = True
    try:
        from transformers import pipeline

        _AUDIO_MODEL = pipeline(
            "audio-classification", model=get_settings().audio_model, device=-1
        )
        logger.info("Loaded audio deepfake classifier")
    except Exception as exc:  # pragma: no cover
        logger.warning("Audio deepfake model unavailable: %s", exc)
        _AUDIO_MODEL = None
    return _AUDIO_MODEL


def audio_model_loaded() -> bool:
    return _AUDIO_MODEL is not None


def _spoof_prob(preds) -> float | None:
    if not preds:
        return None
    fake = real = None
    for item in preds:
        label = str(item.get("label", "")).lower()
        score = float(item.get("score", 0.0))
        if any(t in label for t in _FAKE_TOKENS):
            fake = max(fake or 0.0, score)
        elif any(t in label for t in _REAL_TOKENS):
            real = max(real or 0.0, score)
    if fake is not None:
        return fake
    if real is not None:
        return 1.0 - real
    return None


def _get_whisper():
    global _WHISPER, _WHISPER_TRIED
    if _WHISPER is not None or _WHISPER_TRIED:
        return _WHISPER
    _WHISPER_TRIED = True
    try:
        from faster_whisper import WhisperModel

        from app.config import get_settings

        model = get_settings().whisper_model
        _WHISPER = WhisperModel(model, device="cpu", compute_type="int8")
        logger.info("Loaded faster-whisper model: %s", model)
    except Exception as exc:  # pragma: no cover
        logger.warning("Whisper unavailable: %s", exc)
        _WHISPER = None
    return _WHISPER


class AudioEngine(Engine):
    name = "audio"

    def __init__(self, text_engine=None) -> None:
        self._text_engine = text_engine

    def analyze(self, payload: Payload) -> EvidenceBundle:
        settings = get_settings()
        bundle = self._bundle(Modality.AUDIO)
        data = payload.data
        if not data:
            bundle.error = "no audio bytes"
            return bundle

        y, sr = self._load_audio(data)
        if y is None:
            bundle.error = "cannot decode audio"
            return bundle

        bundle.extras["duration_sec"] = round(len(y) / sr, 2) if sr else None
        self._spectral_checks(bundle, y, sr)

        # Learned deepfake / voice-clone detector (dominant signal when present).
        if settings.enable_audio_model:
            self._deepfake_model_check(bundle, y, sr)

        # Optional transcription + transcript scam analysis.
        if settings.enable_whisper:
            self._transcribe_and_analyze(bundle, data, payload)
        return bundle

    def _deepfake_model_check(self, bundle: EvidenceBundle, y: np.ndarray, sr: int) -> None:
        model = _get_audio_model()
        if model is None:
            return
        try:
            prob = _spoof_prob(model({"raw": y, "sampling_rate": sr}))
        except Exception as exc:  # pragma: no cover
            logger.warning("Audio model inference failed: %s", exc)
            return
        if prob is None:
            return
        # Confidence-tiered so a borderline call doesn't over-penalise real voice.
        if prob >= 0.8:
            weight, reason = 2.0, (
                f"Voice/audio spoof detector strongly flags this as synthetic or "
                f"cloned ({int(prob * 100)}% confidence).")
        elif prob >= 0.6:
            weight, reason = 0.9, (
                f"Voice/audio spoof detector weakly leans toward synthetic "
                f"({int(prob * 100)}%, low confidence).")
        else:
            weight, reason = 0.6, (
                f"Voice/audio spoof detector considers the voice likely genuine "
                f"({int((1 - prob) * 100)}% real).")
        bundle.add("audio_deepfake_model", prob, reason,
                   Component.AI, weight=weight, spoof_prob=round(prob, 4))

        # Model override: a confident "genuine voice" verdict supersedes the
        # unreliable spectral heuristic (which can flag noisy-but-real audio).
        if prob <= 0.2:
            bundle.items = [e for e in bundle.items if e.signal != "synthetic_voice_spectral"]

    def _load_audio(self, data: bytes):
        try:
            import librosa

            y, sr = librosa.load(io.BytesIO(data), sr=16000, mono=True)
            if y is None or len(y) == 0:
                return None, None
            return y.astype(np.float32), sr
        except Exception as exc:
            logger.warning("librosa load failed: %s", exc)
            return None, None

    def _spectral_checks(self, bundle: EvidenceBundle, y: np.ndarray, sr: int) -> None:
        try:
            import librosa
        except Exception:  # pragma: no cover
            return

        # Spectral flatness: synthetic/vocoded speech is often flatter and more
        # uniform than natural speech across time.
        flatness = librosa.feature.spectral_flatness(y=y)[0]
        flat_mean = float(np.mean(flatness))
        flat_std = float(np.std(flatness))

        # MFCC temporal variance: cloned voices tend to have lower prosodic
        # variability (more monotone).
        mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
        mfcc_var = float(np.mean(np.var(mfcc, axis=1)))

        # Zero-crossing regularity.
        zcr = librosa.feature.zero_crossing_rate(y)[0]
        zcr_cov = float(np.std(zcr) / (np.mean(zcr) + 1e-6))

        synth = 0.0
        reasons = []
        if flat_mean > 0.10:
            synth = max(synth, 0.55)
            reasons.append("elevated spectral flatness (vocoder-like)")
        if mfcc_var < 40.0:
            synth = max(synth, 0.5)
            reasons.append("low prosodic/MFCC variability (monotone, cloning-like)")
        if zcr_cov < 0.35:
            synth = max(synth, 0.45)
            reasons.append("unnaturally regular zero-crossing pattern")

        if synth > 0:
            bundle.add("synthetic_voice_spectral", round(synth, 3),
                       "Voice shows " + ", ".join(reasons) + ".",
                       Component.AI, weight=1.0,
                       flatness=round(flat_mean, 4),
                       mfcc_var=round(mfcc_var, 3),
                       zcr_cov=round(zcr_cov, 3))
        else:
            bundle.add("voice_natural_spectral", 0.15,
                       "Spectral features are broadly consistent with natural speech.",
                       Component.AI, weight=0.5)

        # Silence / clipping check — replayed or spliced audio hints.
        rms = float(np.sqrt(np.mean(y ** 2)))
        if rms < 1e-3:
            bundle.add("near_silence", 0.2,
                       "Audio is near-silent; limited signal for analysis.",
                       Component.METADATA, weight=0.4)

    def _transcribe_and_analyze(self, bundle, data, payload) -> None:
        model = _get_whisper()
        if model is None:
            return
        import tempfile, os

        tmp_path = None
        try:
            suffix = os.path.splitext(payload.filename or "audio.wav")[1] or ".wav"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(data)
                tmp_path = tmp.name
            segments, _info = model.transcribe(tmp_path, beam_size=1)
            transcript = " ".join(s.text for s in segments).strip()
            bundle.extras["transcript"] = transcript
            if transcript and self._text_engine is not None:
                from app.engines.base import Payload as _P

                sub = self._text_engine.safe_analyze(
                    _P(modality=Modality.TEXT, text=transcript, source=payload.source)
                )
                # Merge transcript-derived phishing/scam evidence.
                for item in sub.items:
                    if item.component in (Component.PHISHING, Component.AI):
                        item.reason = f"[Transcript] {item.reason}"
                        bundle.items.append(item)
        except Exception as exc:  # pragma: no cover
            logger.warning("transcription failed: %s", exc)
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
