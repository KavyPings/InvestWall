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

# Lazily-initialised classifiers (optional, flag-gated).
_IMAGE_MODEL = None            # deepfake / face-manipulation (runs on face crops)
_IMAGE_MODEL_TRIED = False
_IMAGE_AI_MODEL = None          # general AI-generated-image (runs on whole image)
_IMAGE_AI_MODEL_TRIED = False

_FAKE_LABEL_TOKENS = ("fake", "ai", "artificial", "synthetic", "generated", "spoof", "deepfake")
_REAL_LABEL_TOKENS = ("real", "human", "authentic", "genuine", "natural")


def _load_pipeline(model_name: str):
    from transformers import pipeline

    return pipeline("image-classification", model=model_name, device=-1)


def _get_image_model():
    global _IMAGE_MODEL, _IMAGE_MODEL_TRIED
    if _IMAGE_MODEL is not None or _IMAGE_MODEL_TRIED:
        return _IMAGE_MODEL
    _IMAGE_MODEL_TRIED = True
    try:
        from app.config import get_settings

        _IMAGE_MODEL = _load_pipeline(get_settings().image_model)
        logger.info("Loaded deepfake image classifier")
    except Exception as exc:  # pragma: no cover
        logger.warning("Deepfake image model unavailable: %s", exc)
        _IMAGE_MODEL = None
    return _IMAGE_MODEL


def _get_image_ai_model():
    global _IMAGE_AI_MODEL, _IMAGE_AI_MODEL_TRIED
    if _IMAGE_AI_MODEL is not None or _IMAGE_AI_MODEL_TRIED:
        return _IMAGE_AI_MODEL
    _IMAGE_AI_MODEL_TRIED = True
    try:
        from app.config import get_settings

        _IMAGE_AI_MODEL = _load_pipeline(get_settings().image_ai_model)
        logger.info("Loaded AI-generated-image classifier")
    except Exception as exc:  # pragma: no cover
        logger.warning("AI-image model unavailable: %s", exc)
        _IMAGE_AI_MODEL = None
    return _IMAGE_AI_MODEL


def image_model_loaded() -> bool:
    return _IMAGE_MODEL is not None


def image_ai_model_loaded() -> bool:
    return _IMAGE_AI_MODEL is not None


def _fake_prob(preds) -> float | None:
    """Extract P(fake) from a classifier's predictions using label tokens."""
    if not preds:
        return None
    fake = real = None
    for item in preds:
        label = str(item.get("label", "")).lower()
        score = float(item.get("score", 0.0))
        if any(t in label for t in _FAKE_LABEL_TOKENS):
            fake = max(fake or 0.0, score)
        elif any(t in label for t in _REAL_LABEL_TOKENS):
            real = max(real or 0.0, score)
    if fake is not None:
        return fake
    if real is not None:
        return 1.0 - real
    top = max(preds, key=lambda p: p.get("score", 0.0))
    return float(top.get("score", 0.0))


def score_image_models(rgb: "np.ndarray") -> tuple[float | None, int, float | None]:
    """Shared model scoring for images & video frames.

    Returns ``(deepfake_prob, num_faces, ai_generated_prob)``:
    - ``deepfake_prob``: max P(fake) over detected face crops, or None when no
      face is found (we abstain rather than feed a non-face to a face model).
    - ``ai_generated_prob``: P(AI-generated) over the whole image (non-face
      synthetic content), or None if that model is unavailable.
    """
    from PIL import Image

    from app.config import get_settings
    from app.engines.face_detect import crop_face, detect_faces

    settings = get_settings()
    rgb8 = rgb.astype("uint8") if rgb.dtype != np.uint8 else rgb

    deepfake_prob = None
    num_faces = 0
    if settings.enable_image_model:
        faces = detect_faces(rgb8)
        num_faces = len(faces)
        model = _get_image_model()
        if model is not None and faces:
            probs = []
            for box in sorted(faces, key=lambda b: b[2] * b[3], reverse=True)[:5]:
                crop = crop_face(rgb8, box)
                if crop.size == 0:
                    continue
                probs.append(_fake_prob(model(Image.fromarray(crop))) or 0.0)
            if probs:
                deepfake_prob = max(probs)

    ai_prob = None
    if settings.enable_image_model:
        ai_model = _get_image_ai_model()
        if ai_model is not None:
            ai_prob = _fake_prob(ai_model(Image.fromarray(rgb8)))

    return deepfake_prob, num_faces, ai_prob


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

        # --- Learned models: deepfake (on face crops) + AI-generated (whole) ---
        if get_settings().enable_image_model:
            self._model_ensemble(bundle, np.asarray(rgb))
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

    def _model_ensemble(self, bundle: EvidenceBundle, rgb: "np.ndarray") -> None:
        """Face-crop deepfake model (abstains without a face) + whole-image
        AI-generated detector. The stronger dominates fusion via the weighted-max
        component blend."""
        try:
            deepfake_prob, num_faces, ai_prob = score_image_models(rgb)
        except Exception as exc:  # pragma: no cover
            logger.warning("Image model inference failed: %s", exc)
            return

        bundle.extras["faces_detected"] = num_faces

        # Deepfake / face-manipulation — only when a face was actually found.
        # Confidence-tiered weighting: a decisive call dominates fusion, but a
        # borderline one (0.5-0.7) is down-weighted so it doesn't false-positive
        # ordinary photos of people.
        # Off-the-shelf deepfake detectors are confident on true fakes (~0.97) but
        # have a false-positive tail on ordinary photos because the Haar crop
        # alignment differs from their training alignment. So only a *high*-
        # confidence call carries strong weight; the mid-band is treated as a weak
        # lean, and low scores as (mild) authenticity evidence.
        if deepfake_prob is not None:
            if deepfake_prob >= 0.8:
                weight = 2.0
                reason = (f"Deepfake detector strongly flags the face(s) as "
                          f"manipulated ({int(deepfake_prob * 100)}% confidence, "
                          f"{num_faces} face(s) checked).")
            elif deepfake_prob >= 0.6:
                weight = 0.8
                reason = (f"Deepfake detector weakly leans toward manipulated "
                          f"faces ({int(deepfake_prob * 100)}%, low confidence) "
                          f"across {num_faces} face(s).")
            else:
                weight = 0.6
                reason = (f"Deepfake detector considers the face(s) likely "
                          f"authentic ({int((1 - deepfake_prob) * 100)}% real).")
            bundle.add(
                "deepfake_model", deepfake_prob, reason,
                Component.AI, weight=weight, faces=num_faces,
                fake_prob=round(deepfake_prob, 4),
            )
        elif num_faces == 0 and get_settings().enable_image_model:
            bundle.extras["deepfake_model"] = "skipped (no face detected)"

        # General AI-generated-image detector — whole image (charts, screenshots…)
        if ai_prob is not None:
            if ai_prob >= 0.55:
                bundle.add(
                    "ai_generated_model", ai_prob,
                    f"AI-image detector flags this as likely AI-generated "
                    f"({int(ai_prob * 100)}% confidence).",
                    Component.AI, weight=1.5, ai_prob=round(ai_prob, 4),
                )
            elif ai_prob <= 0.35:
                bundle.add(
                    "ai_generated_model", ai_prob,
                    f"AI-image detector considers this likely a real photo "
                    f"({int((1 - ai_prob) * 100)}%).",
                    Component.AI, weight=0.8, ai_prob=round(ai_prob, 4),
                )
            # 0.35–0.55: uncertain — abstain (no signal) to avoid noise.

        # Model override: when a learned model is confident the image is real,
        # drop the classical heuristics that also fire on legit screenshots /
        # re-saved images (no EXIF, uniform ELA, smooth noise). The model is far
        # more reliable than these, and this prevents false-positive scores on
        # ordinary screenshots (e.g. a genuine SEBI document capture).
        model_says_real = (
            (ai_prob is not None and ai_prob <= 0.2)
            or (deepfake_prob is not None and deepfake_prob <= 0.3)
        )
        if model_says_real:
            noisy = {
                "ela_uniform", "low_noise_residual", "spectral_anomaly",
                "missing_exif", "no_camera_metadata", "face_over_symmetry",
            }
            bundle.items = [e for e in bundle.items if e.signal not in noisy]

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
            # Missing EXIF is the NORM for screenshots, WhatsApp/social images and
            # any re-saved image — so it's only a very mild signal on its own.
            bundle.add("missing_exif", 0.2,
                       "No embedded camera metadata (normal for screenshots, "
                       "social media, and re-saved images).",
                       Component.METADATA, weight=0.3)
        elif not has_camera and fmt in {"PNG", "WEBP"}:
            bundle.add("no_camera_metadata", 0.2,
                       "No camera make/model in metadata (typical for screenshots).",
                       Component.METADATA, weight=0.3)

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
