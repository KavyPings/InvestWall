"""Module 3 — Video Analysis Engine (PRD §6).

Pipeline: frame extraction (OpenCV, no system FFmpeg needed) -> per-frame image
forensics (reuses ImageEngine heuristics) -> temporal consistency -> blink /
face-motion heuristics -> frame aggregation -> final score.
"""
from __future__ import annotations

import logging
import tempfile
import os

import numpy as np

from app.config import get_settings
from app.core.evidence import Component, EvidenceBundle, Modality
from app.engines.base import Engine, Payload

logger = logging.getLogger("investwall.engine.video")


class VideoEngine(Engine):
    name = "video"

    def analyze(self, payload: Payload) -> EvidenceBundle:
        settings = get_settings()
        bundle = self._bundle(Modality.VIDEO)
        data = payload.data
        if not data:
            bundle.error = "no video bytes"
            return bundle

        try:
            import cv2
        except Exception:  # pragma: no cover
            bundle.error = "OpenCV unavailable for video decoding"
            return bundle

        tmp_path = None
        try:
            suffix = os.path.splitext(payload.filename or "video.mp4")[1] or ".mp4"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(data)
                tmp_path = tmp.name

            cap = cv2.VideoCapture(tmp_path)
            if not cap.isOpened():
                bundle.error = "cannot open video"
                return bundle

            total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
            fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
            n = max(4, min(settings.video_sample_frames, total or settings.video_sample_frames))
            idxs = self._sample_indices(total, n)

            frames = self._grab_frames(cv2, cap, idxs)
            cap.release()

            bundle.extras["frames_analyzed"] = len(frames)
            bundle.extras["duration_sec"] = round(total / fps, 2) if fps else None
            if not frames:
                bundle.error = "no frames extracted"
                return bundle

            self._face_and_temporal(bundle, cv2, frames, fps)

            # Learned model pass: face-crop → deepfake model per frame.
            if settings.enable_image_model:
                self._model_pass(bundle, cv2, frames)
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:  # pragma: no cover
                    pass
        return bundle

    def _model_pass(self, bundle, cv2, frames) -> None:
        """Run the image deepfake/AI models over a subset of frames and
        aggregate (max fake probability across frames)."""
        from app.engines.image_engine import score_image_models

        # Cap the number of frames sent to the model to keep latency reasonable.
        step = max(1, len(frames) // 6)
        sampled = frames[::step][:6]

        deepfake_probs, ai_probs, face_frames = [], [], 0
        for frame in sampled:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            try:
                df, nfaces, ai = score_image_models(rgb)
            except Exception:  # pragma: no cover
                continue
            if nfaces:
                face_frames += 1
            if df is not None:
                deepfake_probs.append(df)
            if ai is not None:
                ai_probs.append(ai)

        if deepfake_probs:
            top = max(deepfake_probs)
            if top >= 0.5:
                reason = (f"Deepfake model flags manipulated faces in "
                          f"{sum(p >= 0.5 for p in deepfake_probs)}/{len(deepfake_probs)} "
                          f"sampled frames (peak {int(top * 100)}%).")
            else:
                reason = (f"Deepfake model considers the faces authentic across "
                          f"sampled frames (peak {int(top * 100)}% fake).")
            bundle.add("video_deepfake_model", top, reason,
                       Component.AI, weight=2.2, frames=len(deepfake_probs))
        if ai_probs and max(ai_probs) >= 0.6:
            bundle.add("video_ai_generated_model", max(ai_probs),
                       f"AI-image model flags frames as likely AI-generated "
                       f"(peak {int(max(ai_probs) * 100)}%).",
                       Component.AI, weight=1.4)

    @staticmethod
    def _sample_indices(total: int, n: int) -> list[int]:
        if total <= 0:
            return list(range(n))
        if total <= n:
            return list(range(total))
        step = total / float(n)
        return [int(i * step) for i in range(n)]

    @staticmethod
    def _grab_frames(cv2, cap, idxs):
        frames = []
        for idx in idxs:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ok, frame = cap.read()
            if not ok or frame is None:
                continue
            frames.append(frame)
        return frames

    def _face_and_temporal(self, bundle, cv2, frames, fps) -> None:
        cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        eye_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_eye.xml"
        )
        have_cascade = not cascade.empty()

        grays = [cv2.cvtColor(f, cv2.COLOR_BGR2GRAY) for f in frames]

        # --- Temporal consistency: frame-to-frame difference variability. ---
        diffs = []
        for a, b in zip(grays, grays[1:]):
            if a.shape != b.shape:
                b = cv2.resize(b, (a.shape[1], a.shape[0]))
            diffs.append(float(np.abs(a.astype(np.float32) - b.astype(np.float32)).mean()))
        if diffs:
            mean_d = sum(diffs) / len(diffs)
            var_d = sum((d - mean_d) ** 2 for d in diffs) / len(diffs)
            cov = (var_d ** 0.5) / mean_d if mean_d else 0.0
            # Erratic inter-frame changes (high CoV) hint at frame-level
            # generation/splicing inconsistencies.
            if cov > 1.2:
                bundle.add("temporal_inconsistency", min(0.4 + cov / 6.0, 0.85),
                           "Inter-frame changes are erratic, suggesting temporal "
                           "artefacts typical of manipulated/deepfake video.",
                           Component.AI, weight=1.0, frame_diff_cov=round(cov, 3))

        # --- Face tracking + blink + per-frame smoothness. ---
        face_frames = 0
        blink_frames = 0
        smooth_hits = 0
        for gray in grays:
            if have_cascade:
                faces = cascade.detectMultiScale(gray, 1.1, 5, minSize=(40, 40))
                if len(faces):
                    face_frames += 1
                    fx, fy, fw, fh = max(faces, key=lambda f: f[2] * f[3])
                    roi = gray[fy:fy + fh, fx:fx + fw]
                    if not eye_cascade.empty():
                        eyes = eye_cascade.detectMultiScale(roi, 1.1, 6)
                        if len(eyes) < 2:
                            blink_frames += 1
            # smoothness residual per frame
            lap = cv2.Laplacian(gray, cv2.CV_64F)
            if float(lap.var()) < 60.0:
                smooth_hits += 1

        bundle.extras["face_frames"] = face_frames
        nf = len(grays)

        if face_frames:
            blink_rate = blink_frames / max(face_frames, 1)
            # Natural blinking gives an intermediate rate; near-zero blinking is a
            # classic early-deepfake tell, and constant "closed" also anomalous.
            if blink_rate < 0.02:
                bundle.add("no_blinking", 0.6,
                           "Subject shows almost no blinking across sampled "
                           "frames — a known deepfake indicator.",
                           Component.AI, weight=0.8, blink_rate=round(blink_rate, 3))
            bundle.add("face_track", 0.15,
                       f"Face present in {face_frames}/{nf} sampled frames "
                       "(impersonation-relevant content).",
                       Component.AI, weight=0.2)

        if smooth_hits / max(nf, 1) > 0.6:
            bundle.add("frame_oversmoothing", 0.5,
                       "Most frames are unusually smooth/low-detail, consistent "
                       "with neural rendering.",
                       Component.AI, weight=0.6,
                       smooth_ratio=round(smooth_hits / max(nf, 1), 3))
