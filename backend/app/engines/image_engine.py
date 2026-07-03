"""Module 2 — Image Analysis Engine (PRD §6).

Pipeline: metadata extraction -> noise/FFT analysis -> compression (ELA) ->
face detection -> AI-artifact heuristics -> evidence generation.

All checks are real computations over the image bytes using Pillow/NumPy/OpenCV.
No model weights are required; heavier deepfake models can be added behind this
same interface later.
"""
from __future__ import annotations

import io
import logging

import numpy as np

from app.config import get_settings
from app.core.evidence import Component, EvidenceBundle, Modality
from app.engines.base import Engine, Payload

logger = logging.getLogger("investwall.engine.image")

# AI-generation software / watermark fingerprints found in metadata or bytes.
_AI_SOFTWARE_TOKENS = [
    b"stable diffusion", b"stablediffusion", b"midjourney", b"dall-e", b"dalle",
    b"dall\xc2\xb7e", b"firefly", b"adobe firefly", b"generativeai", b"gpt-4o",
    b"leonardo.ai", b"nightcafe", b"comfyui", b"automatic1111", b"invokeai",
    b"c2pa", b"contentcredentials", b"gemini", b"imagen", b"flux.1", b"ideogram",
]


class ImageEngine(Engine):
    name = "image"

    def analyze(self, payload: Payload) -> EvidenceBundle:
        bundle = self._bundle(Modality.IMAGE)
        data = payload.data
        if not data:
            bundle.error = "no image bytes"
            return bundle

        # --- Watermark / provenance token scan over raw bytes ---
        self._scan_ai_tokens(bundle, data)

        try:
            from PIL import Image
        except Exception:  # pragma: no cover
            bundle.error = "Pillow unavailable"
            return bundle

        try:
            img = Image.open(io.BytesIO(data))
            img.load()
        except Exception as exc:
            bundle.error = f"cannot decode image: {exc}"
            return bundle

        self._metadata_checks(bundle, img, data)

        rgb = img.convert("RGB")
        arr = np.asarray(rgb, dtype=np.float32)
        self._noise_fft_checks(bundle, arr)
        self._ela_check(bundle, rgb)
        self._face_checks(bundle, arr)
        return bundle

    # ---- metadata ----
    def _scan_ai_tokens(self, bundle: EvidenceBundle, data: bytes) -> None:
        low = data[:200_000].lower()
        for token in _AI_SOFTWARE_TOKENS:
            if token in low:
                name = token.decode("latin-1", "ignore")
                bundle.add("ai_watermark_metadata", 0.9,
                           f"Image embeds an AI-generation marker ('{name}').",
                           Component.AI, weight=1.4, token=name)
                return

    def _metadata_checks(self, bundle: EvidenceBundle, img, data: bytes) -> None:
        exif = None
        try:
            exif = img.getexif()
        except Exception:
            exif = None

        has_camera = False
        software = ""
        if exif:
            make = exif.get(271)  # Make
            model = exif.get(272)  # Model
            software = str(exif.get(305, "") or "")  # Software
            has_camera = bool(make or model)
            if software:
                low = software.lower()
                if any(t in low for t in ("photoshop", "gimp", "snapseed", "lightroom")):
                    bundle.add("edited_software", 0.35,
                               f"Image was processed by editing software ({software}).",
                               Component.METADATA, weight=0.6, software=software)

        fmt = (getattr(img, "format", "") or "").upper()
        if not exif or len(list(exif.items())) == 0:
            # No EXIF at all is common for AI images and screenshots.
            bundle.add("missing_exif", 0.45,
                       "Image has no EXIF metadata (common for AI-generated or "
                       "re-saved images).",
                       Component.METADATA, weight=0.7)
        elif not has_camera and fmt in {"PNG", "WEBP"}:
            bundle.add("no_camera_metadata", 0.4,
                       "No camera make/model in metadata.",
                       Component.METADATA, weight=0.6)

    # ---- noise / frequency ----
    def _noise_fft_checks(self, bundle: EvidenceBundle, arr: np.ndarray) -> None:
        gray = arr.mean(axis=2)
        h, w = gray.shape
        if h < 32 or w < 32:
            return

        # Residual noise via Laplacian; GAN/diffusion images often have unusually
        # smooth, low-variance high-frequency residuals.
        lap = (
            -4 * gray
            + np.roll(gray, 1, 0) + np.roll(gray, -1, 0)
            + np.roll(gray, 1, 1) + np.roll(gray, -1, 1)
        )
        noise_std = float(lap.std())
        # Normalise: very low residual noise -> more likely synthetic/over-smooth.
        smoothness = max(0.0, 1.0 - min(noise_std / 12.0, 1.0))
        if smoothness > 0.55:
            bundle.add("low_noise_residual", round(0.5 + 0.4 * smoothness, 3),
                       "Unusually smooth high-frequency noise, consistent with "
                       "GAN/diffusion-generated imagery.",
                       Component.AI, weight=0.9, noise_std=round(noise_std, 3))

        # FFT high-frequency energy ratio — periodic diffusion artefacts show up
        # as regular spectral peaks.
        f = np.fft.fftshift(np.abs(np.fft.fft2(gray - gray.mean())))
        cy, cx = h // 2, w // 2
        r = min(h, w) // 8 or 1
        low_energy = float(f[cy - r:cy + r, cx - r:cx + r].sum())
        total_energy = float(f.sum()) or 1.0
        high_ratio = 1.0 - (low_energy / total_energy)
        if high_ratio > 0.985:
            bundle.add("spectral_anomaly", 0.55,
                       "Frequency spectrum shows atypical high-frequency energy "
                       "distribution (possible generative artefacts).",
                       Component.AI, weight=0.6, high_freq_ratio=round(high_ratio, 4))

    # ---- ELA (Error Level Analysis) ----
    def _ela_check(self, bundle: EvidenceBundle, rgb) -> None:
        try:
            from PIL import Image, ImageChops

            buf = io.BytesIO()
            rgb.save(buf, "JPEG", quality=90)
            buf.seek(0)
            recompressed = Image.open(buf)
            diff = ImageChops.difference(rgb, recompressed)
            ela = np.asarray(diff, dtype=np.float32)
            mean_err = float(ela.mean())
            max_err = float(ela.max()) or 1.0
            # Highly uniform ELA (little variance) suggests a single synthetic
            # generation pass rather than a spliced/edited photograph.
            err_std = float(ela.std())
            uniformity = max(0.0, 1.0 - min(err_std / 8.0, 1.0))
            if mean_err < 1.2 and uniformity > 0.6:
                bundle.add("ela_uniform", 0.5,
                           "Error-Level-Analysis is uniform, consistent with a "
                           "fully generated (not photographed) image.",
                           Component.AI, weight=0.7,
                           ela_mean=round(mean_err, 3), ela_std=round(err_std, 3))
            elif err_std > 18 and max_err > 60:
                bundle.add("ela_splice", 0.55,
                           "Error-Level-Analysis shows localised inconsistencies "
                           "suggestive of splicing/editing.",
                           Component.METADATA, weight=0.7,
                           ela_std=round(err_std, 3))
        except Exception:  # pragma: no cover
            pass

    # ---- faces ----
    def _face_checks(self, bundle: EvidenceBundle, arr: np.ndarray) -> None:
        try:
            import cv2
        except Exception:  # pragma: no cover
            return
        try:
            gray = arr.mean(axis=2).astype("uint8")
            cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            cascade = cv2.CascadeClassifier(cascade_path)
            if cascade.empty():
                return
            faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5,
                                             minSize=(40, 40))
            bundle.extras["face_count"] = int(len(faces))
            if len(faces) == 0:
                return
            bundle.add("face_present", 0.1,
                       f"Detected {len(faces)} face(s); portrait content is a "
                       "common deepfake/impersonation target.",
                       Component.AI, weight=0.2, faces=int(len(faces)))
            # Symmetry / eye-region regularity heuristic on the largest face.
            fx, fy, fw, fh = max(faces, key=lambda f: f[2] * f[3])
            face = gray[fy:fy + fh, fx:fx + fw].astype(np.float32)
            if face.size and fw > 20:
                left = face[:, : fw // 2]
                right = np.fliplr(face[:, fw - fw // 2:])
                m = min(left.shape[1], right.shape[1])
                if m > 0:
                    asym = float(np.abs(left[:, :m] - right[:, :m]).mean())
                    # GAN faces are often *too* symmetric.
                    if asym < 8.0:
                        bundle.add("face_over_symmetry", 0.55,
                                   "Facial symmetry is unnaturally high, a known "
                                   "trait of GAN-generated faces.",
                                   Component.AI, weight=0.7, asymmetry=round(asym, 3))
        except Exception:  # pragma: no cover
            pass
