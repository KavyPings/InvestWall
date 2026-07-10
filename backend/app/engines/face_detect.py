"""Face detection utility for the image/video engines.

Deepfake/face-manipulation models are trained on *aligned face crops*; feeding
them a whole scene destroys accuracy (measured: ~95% recall on a face crop vs
~0% on the same face inside a larger image). So we detect faces first and crop.

Detector priority:
  1. MediaPipe FaceDetection (if importable) — robust on tilted/profile faces.
  2. OpenCV Haar, multi-cascade + horizontal flip + small rotations — always
     available (ships with opencv), meaningfully better than a single frontal
     cascade for the profile/tilted faces common in deepfakes.
"""
from __future__ import annotations

import logging

import numpy as np

logger = logging.getLogger("investwall.face")

Box = tuple[int, int, int, int]  # x, y, w, h

_MP = None
_MP_TRIED = False


def _get_mediapipe():
    """Return a MediaPipe FaceDetection instance, or None if unavailable."""
    global _MP, _MP_TRIED
    if _MP is not None or _MP_TRIED:
        return _MP
    _MP_TRIED = True
    try:
        import importlib

        fd = importlib.import_module("mediapipe.python.solutions.face_detection")
        _MP = fd.FaceDetection(model_selection=1, min_detection_confidence=0.5)
        logger.info("Using MediaPipe face detector")
    except Exception:
        _MP = None  # fall back to Haar
    return _MP


def detect_faces(rgb: np.ndarray, min_size: int = 40) -> list[Box]:
    """Detect faces in an RGB uint8 image. Returns deduped (x, y, w, h) boxes."""
    if rgb is None or rgb.ndim != 3:
        return []
    boxes = _mediapipe_faces(rgb)
    if boxes is None:
        boxes = _haar_faces(rgb, min_size)
    return _dedupe(boxes)


def _mediapipe_faces(rgb: np.ndarray) -> list[Box] | None:
    mp = _get_mediapipe()
    if mp is None:
        return None
    try:
        h, w = rgb.shape[:2]
        res = mp.process(rgb)
        out: list[Box] = []
        for det in getattr(res, "detections", None) or []:
            bb = det.location_data.relative_bounding_box
            x, y = int(bb.xmin * w), int(bb.ymin * h)
            bw, bh = int(bb.width * w), int(bb.height * h)
            if bw > 20 and bh > 20:
                out.append((max(0, x), max(0, y), bw, bh))
        return out
    except Exception:  # pragma: no cover
        return None


def _haar_faces(rgb: np.ndarray, min_size: int) -> list[Box]:
    import cv2

    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    h, w = gray.shape
    cascades = [
        cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_alt2.xml"),
        cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml"),
        cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_profileface.xml"),
    ]
    cascades = [c for c in cascades if not c.empty()]
    boxes: list[Box] = []

    def run(img, mapper=None):
        for c in cascades:
            for (x, y, fw, fh) in c.detectMultiScale(img, 1.1, 5, minSize=(min_size, min_size)):
                boxes.append(mapper((x, y, fw, fh)) if mapper else (int(x), int(y), int(fw), int(fh)))

    # Upright.
    run(gray)
    # Horizontal flip catches right-facing profiles (profileface is left-only).
    run(cv2.flip(gray, 1), mapper=lambda b: (w - b[0] - b[2], b[1], b[2], b[3]))
    # Small rotations catch tilted faces; map box centre back to upright coords.
    for angle in (-20, 20):
        m = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
        rot = cv2.warpAffine(gray, m, (w, h))
        inv = cv2.getRotationMatrix2D((w / 2, h / 2), -angle, 1.0)

        def back(b, inv=inv):
            cx, cy = b[0] + b[2] / 2, b[1] + b[3] / 2
            ox = inv[0, 0] * cx + inv[0, 1] * cy + inv[0, 2]
            oy = inv[1, 0] * cx + inv[1, 1] * cy + inv[1, 2]
            s = int(max(b[2], b[3]) * 1.1)
            return (int(ox - s / 2), int(oy - s / 2), s, s)

        run(rot, mapper=back)

    # Clamp to image bounds.
    clamped = []
    for (x, y, fw, fh) in boxes:
        x, y = max(0, x), max(0, y)
        fw, fh = min(fw, w - x), min(fh, h - y)
        if fw > 20 and fh > 20:
            clamped.append((x, y, fw, fh))
    return clamped


def _iou(a: Box, b: Box) -> float:
    ax2, ay2 = a[0] + a[2], a[1] + a[3]
    bx2, by2 = b[0] + b[2], b[1] + b[3]
    ix1, iy1 = max(a[0], b[0]), max(a[1], b[1])
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0, ix2 - ix1), max(0, iy2 - iy1)
    inter = iw * ih
    union = a[2] * a[3] + b[2] * b[3] - inter
    return inter / union if union else 0.0


def _dedupe(boxes: list[Box], iou_thresh: float = 0.4) -> list[Box]:
    kept: list[Box] = []
    for box in sorted(boxes, key=lambda b: b[2] * b[3], reverse=True):
        if all(_iou(box, k) < iou_thresh for k in kept):
            kept.append(box)
    return kept


def crop_face(rgb: np.ndarray, box: Box, margin: float = 0.3) -> np.ndarray:
    """Crop a face box with margin (models expect some context around the face)."""
    h, w = rgb.shape[:2]
    x, y, bw, bh = box
    mx, my = int(bw * margin), int(bh * margin)
    x1, y1 = max(0, x - mx), max(0, y - my)
    x2, y2 = min(w, x + bw + mx), min(h, y + bh + my)
    return rgb[y1:y2, x1:x2]
