#!/usr/bin/env python3
"""Archive and extract the PO's five real handwritten button-bracket pairs."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / "Branding" / "CEOKlaue"
RAW = WORK / "00_raw"
EXTRACTED = WORK / "01_extracted" / "button_brackets"
VECTORS = WORK / "02_vectors" / "button_brackets"
RUNTIME = ROOT / "App" / "static" / "ceoklaue-ui" / "button-brackets"
MANIFEST = WORK / "button-bracket-source-manifest.json"
SOURCE = {
    "filename": "ceoklaue_button_brackets_01.jpg",
    "original_filename": "IMG_7192.JPG",
    "sha256": "ff3216183427dc96f85fe88b3fa595d46c0f1c3a04f6f38fbefc110dda39d3db",
    "pixel_dimensions": [4032, 3024],
    "oriented_dimensions": [3024, 4032],
}
ROWS = {"left": (1600, 2070), "right": (2160, 2620)}
X_RANGE = (300, 2500)
DETECTION_THRESHOLD = 80
EXTRACTION_THRESHOLD = 105
SAFE_MARGIN = 6
sys.path.insert(0, str(WORK / "03_font"))

from build_ceoklaue import save_png, save_svg  # noqa: E402


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def detect_runs(gray: np.ndarray, y0: int, y1: int) -> list[tuple[int, int, int]]:
    x0, x1 = X_RANGE
    projection = (gray[y0:y1, x0:x1] < DETECTION_THRESHOLD).sum(axis=0)
    active = (projection > 3).astype(np.uint8)[None, :]
    active = cv2.morphologyEx(active, cv2.MORPH_CLOSE, np.ones((1, 55), np.uint8))[0]
    runs = []
    start = None
    for index, value in enumerate(active):
        if value and start is None:
            start = index
        if start is not None and (not value or index == len(active) - 1):
            end = index if not value else index + 1
            ink = int(projection[start:end].sum())
            if end - start > 8 and ink > 1000:
                runs.append((start + x0, end + x0, ink))
            start = None
    return runs


def clean_mask(gray: np.ndarray, box: tuple[int, int, int, int]) -> np.ndarray:
    x0, y0, x1, y1 = box
    mask = np.where(gray[y0:y1, x0:x1] < EXTRACTION_THRESHOLD, 255, 0).astype(np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((2, 2), np.uint8))
    count, labels, stats, _centers = cv2.connectedComponentsWithStats(mask, 8)
    areas = [int(stats[index, cv2.CC_STAT_AREA]) for index in range(1, count)]
    if not areas:
        raise RuntimeError(f"No handwritten bracket ink in crop {box}")
    floor = max(6, int(max(areas) * .035))
    selected = np.zeros_like(mask)
    for index, area in enumerate(areas, 1):
        if area >= floor:
            selected[labels == index] = 255
    selected = cv2.dilate(
        selected, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)), iterations=1
    )
    selected = cv2.morphologyEx(selected, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    points = cv2.findNonZero(selected)
    if points is None:
        raise RuntimeError(f"No retained handwritten bracket ink in crop {box}")
    x, y, width, height = cv2.boundingRect(points)
    crop = selected[y:y + height, x:x + width]
    return cv2.copyMakeBorder(
        crop, SAFE_MARGIN, SAFE_MARGIN, SAFE_MARGIN, SAFE_MARGIN,
        cv2.BORDER_CONSTANT, value=0,
    )


def verify_source() -> Path:
    path = RAW / SOURCE["filename"]
    if not path.is_file() or digest(path) != SOURCE["sha256"]:
        raise RuntimeError(f"Archived button-bracket source missing or changed: {path}")
    with Image.open(path) as image:
        if image.format not in {"JPEG", "MPO"} or list(image.size) != SOURCE["pixel_dimensions"]:
            raise RuntimeError("Unexpected button-bracket source format or dimensions")
        if list(ImageOps.exif_transpose(image).size) != SOURCE["oriented_dimensions"]:
            raise RuntimeError("Unexpected oriented button-bracket dimensions")
    return path


def verify_manifest(manifest: dict) -> None:
    if manifest.get("version") != "CEOKlaue button bracket source import v1":
        raise RuntimeError("Unknown button-bracket manifest version")
    pairs = manifest.get("pairs", [])
    if [pair.get("id") for pair in pairs] != [f"{index:02d}" for index in range(1, 6)]:
        raise RuntimeError("Button-bracket pair inventory changed")
    for pair in pairs:
        for side in ("left", "right"):
            output = pair[side]
            for kind in ("png", "svg", "runtime_svg"):
                path = ROOT / output[kind]["path"]
                if not path.is_file() or digest(path) != output[kind]["sha256"]:
                    raise RuntimeError(f"Button-bracket output changed: {path}")


def import_sources() -> dict:
    source_path = verify_source()
    if MANIFEST.is_file():
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        verify_manifest(manifest)
        print("CEOKlaue button-bracket source already imported and verified")
        return manifest

    gray = np.asarray(ImageOps.exif_transpose(Image.open(source_path)).convert("L"))
    detected = {side: detect_runs(gray, *row) for side, row in ROWS.items()}
    if any(len(runs) != 5 for runs in detected.values()):
        raise RuntimeError(f"Expected five real brackets per side, detected {detected}")

    sides = {"left": [], "right": []}
    with tempfile.TemporaryDirectory(prefix="ceoklaue-button-brackets-") as temporary:
        stage = Path(temporary)
        for side, runs in detected.items():
            y0, y1 = ROWS[side]
            for index, (run_x0, run_x1, ink) in enumerate(runs, 1):
                stem = f"button_bracket_{index:02d}_{side}"
                box = (max(0, run_x0 - 45), y0, min(gray.shape[1], run_x1 + 45), y1)
                mask = clean_mask(gray, box)
                staged_png = stage / f"{stem}.png"
                staged_svg = stage / f"{stem}.svg"
                save_png(mask, staged_png)
                save_svg(mask, staged_svg)
                targets = {
                    "png": EXTRACTED / f"{stem}.png",
                    "svg": VECTORS / f"{stem}.svg",
                    "runtime_svg": RUNTIME / f"{stem}.svg",
                }
                if any(path.exists() for path in targets.values()):
                    raise RuntimeError(f"Refusing to overwrite {stem}")
                for kind, target in targets.items():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(staged_png if kind == "png" else staged_svg, target)
                sides[side].append({
                    "candidate_key": stem,
                    "source_region_id": f"button-bracket-{side}-{index:02d}",
                    "oriented_crop": list(box),
                    "detected_ink_pixels": ink,
                    "mask_dimensions": [int(mask.shape[1]), int(mask.shape[0])],
                    **{
                        kind: {"path": target.relative_to(ROOT).as_posix(), "sha256": digest(target)}
                        for kind, target in targets.items()
                    },
                })

    pairs = [
        {"id": f"{index:02d}", "left": sides["left"][index - 1], "right": sides["right"][index - 1]}
        for index in range(1, 6)
    ]
    manifest = {
        "version": "CEOKlaue button bracket source import v1",
        "source": {**SOURCE, "content": "five real left brackets over five matching real right brackets"},
        "pairing": {
            "method": "same left-to-right column index across source rows",
            "synthetic_variants": False,
            "mirroring": False,
            "pair_integrity_required": True,
        },
        "extraction": {
            "exif_orientation_applied_in_memory": True,
            "detection_threshold": DETECTION_THRESHOLD,
            "extraction_threshold": EXTRACTION_THRESHOLD,
            "safe_margin": SAFE_MARGIN,
        },
        "totals": {"pairs": 5, "left_assets": 5, "right_assets": 5},
        "pairs": pairs,
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    verify_manifest(manifest)
    print("Imported five real handwritten button-bracket pairs")
    return manifest


if __name__ == "__main__":
    import_sources()
