#!/usr/bin/env python3
"""Archive and extract only the PO's final F/H repair candidates."""

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


WORK = Path(__file__).resolve().parent
RAW = WORK / "00_raw"
EXTRACTED = WORK / "01_extracted" / "final_fh_repair"
VECTORS = WORK / "02_vectors" / "final_fh_repair"
MANIFEST = WORK / "final-fh-repair-source-manifest.json"
SOURCE = {
    "filename": "ceoklaue_final_fh_repair_01.jpg",
    "original_filename": "IMG_7191.JPG",
    "sha256": "ca9f18dc2d7903b4f2b10d61009ad106d7f03c9a2d5e0d869f0ab2756d921ad5",
    "pixel_dimensions": [4032, 3024],
    "oriented_dimensions": [3024, 4032],
}
ROWS = (
    ("F", "cap_F", (1580, 1910)),
    ("H", "cap_H", (1900, 2290)),
)
X_RANGE = (500, 2400)
DETECTION_THRESHOLD = 80
EXTRACTION_THRESHOLD = 110
SAFE_MARGIN = 6
sys.path.insert(0, str(WORK / "03_font"))

from build_ceoklaue import save_png, save_svg  # noqa: E402


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def detect_runs(gray: np.ndarray, y0: int, y1: int) -> list[tuple[int, int, int]]:
    x0, x1 = X_RANGE
    projection = (gray[y0:y1, x0:x1] < DETECTION_THRESHOLD).sum(axis=0)
    active = (projection > 2).astype(np.uint8)[None, :]
    active = cv2.morphologyEx(active, cv2.MORPH_CLOSE, np.ones((1, 50), np.uint8))[0]
    runs = []
    start = None
    for index, value in enumerate(active):
        if value and start is None:
            start = index
        if start is not None and (not value or index == len(active) - 1):
            end = index if not value else index + 1
            ink = int(projection[start:end].sum())
            if end - start > 8 and ink >= 600:
                runs.append((start + x0, end + x0, ink))
            start = None
    return runs


def clean_mask(gray: np.ndarray, box: tuple[int, int, int, int]) -> np.ndarray:
    x0, y0, x1, y1 = box
    mask = np.where(gray[y0:y1, x0:x1] < EXTRACTION_THRESHOLD, 255, 0).astype(np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((2, 2), np.uint8))
    count, labels, stats, _centroids = cv2.connectedComponentsWithStats(mask, 8)
    areas = [int(stats[index, cv2.CC_STAT_AREA]) for index in range(1, count)]
    if not areas:
        raise RuntimeError(f"No handwritten ink in crop {box}")
    relative_floor = max(6, int(max(areas) * .04))
    selected = np.zeros_like(mask)
    for index, area in enumerate(areas, 1):
        if area >= relative_floor:
            selected[labels == index] = 255
    selected = cv2.dilate(
        selected, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)), iterations=1
    )
    selected = cv2.morphologyEx(selected, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    points = cv2.findNonZero(selected)
    if points is None:
        raise RuntimeError(f"No retained handwritten ink in crop {box}")
    x, y, width, height = cv2.boundingRect(points)
    crop = selected[y:y + height, x:x + width]
    return cv2.copyMakeBorder(
        crop, SAFE_MARGIN, SAFE_MARGIN, SAFE_MARGIN, SAFE_MARGIN,
        cv2.BORDER_CONSTANT, value=0,
    )


def verify_source() -> Path:
    path = RAW / SOURCE["filename"]
    if not path.is_file() or digest(path) != SOURCE["sha256"]:
        raise RuntimeError(f"Archived F/H repair source missing or changed: {path}")
    with Image.open(path) as image:
        if image.format not in {"JPEG", "MPO"} or list(image.size) != SOURCE["pixel_dimensions"]:
            raise RuntimeError("Unexpected F/H repair source format or dimensions")
        if list(ImageOps.exif_transpose(image).size) != SOURCE["oriented_dimensions"]:
            raise RuntimeError("Unexpected oriented F/H repair source dimensions")
    return path


def verify_manifest(manifest: dict) -> None:
    if manifest.get("version") != "CEOKlaue final F/H repair source import v1":
        raise RuntimeError("Unknown F/H repair manifest version")
    if [record["character"] for record in manifest.get("characters", [])] != ["F", "H"]:
        raise RuntimeError("F/H repair scope changed")
    for record in manifest["characters"]:
        if len(record["outputs"]) != 5:
            raise RuntimeError(f"Expected five candidates for {record['character']}")
        for output in record["outputs"]:
            for kind in ("png", "svg"):
                path = WORK / output[kind]["path"]
                if not path.is_file() or digest(path) != output[kind]["sha256"]:
                    raise RuntimeError(f"F/H repair output changed or disappeared: {path}")


def import_sources() -> dict:
    source_path = verify_source()
    if MANIFEST.is_file():
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        verify_manifest(manifest)
        print("CEOKlaue final F/H repair source already imported and verified")
        return manifest

    gray = np.asarray(ImageOps.exif_transpose(Image.open(source_path)).convert("L"))
    records = []
    with tempfile.TemporaryDirectory(prefix="ceoklaue-final-fh-repair-") as temporary:
        stage = Path(temporary)
        for character, glyph_key, (y0, y1) in ROWS:
            detected = detect_runs(gray, y0, y1)
            if len(detected) != 5:
                raise RuntimeError(f"Expected five new {character}, detected {detected}")
            outputs = []
            for index, (run_x0, run_x1, ink) in enumerate(detected, 1):
                candidate_id = f"{character}{index:02d}"
                stem = f"{glyph_key}_new_{index:02d}"
                target_png = EXTRACTED / f"{stem}.png"
                target_svg = VECTORS / f"{stem}.svg"
                if target_png.exists() or target_svg.exists():
                    raise RuntimeError(f"Refusing to overwrite {stem}")
                box = (max(0, run_x0 - 45), y0, min(gray.shape[1], run_x1 + 45), y1)
                mask = clean_mask(gray, box)
                staged_png = stage / f"{stem}.png"
                staged_svg = stage / f"{stem}.svg"
                save_png(mask, staged_png)
                save_svg(mask, staged_svg)
                target_png.parent.mkdir(parents=True, exist_ok=True)
                target_svg.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(staged_png, target_png)
                shutil.copy2(staged_svg, target_svg)
                outputs.append({
                    "id": candidate_id,
                    "candidate_key": stem,
                    "source_region_id": f"{glyph_key}-new-{index:02d}",
                    "oriented_crop": list(box),
                    "detected_ink_pixels": ink,
                    "mask_dimensions": [int(mask.shape[1]), int(mask.shape[0])],
                    "png": {"path": target_png.relative_to(WORK).as_posix(), "sha256": digest(target_png)},
                    "svg": {"path": target_svg.relative_to(WORK).as_posix(), "sha256": digest(target_svg)},
                })
            records.append({
                "character": character,
                "glyph_key": glyph_key,
                "source": SOURCE["filename"],
                "source_mapping": {
                    "oriented_y_range": [y0, y1],
                    "oriented_x_range": list(X_RANGE),
                    "reading_order": "left_to_right",
                },
                "new_candidate_ids": [output["id"] for output in outputs],
                "outputs": outputs,
            })

    manifest = {
        "version": "CEOKlaue final F/H repair source import v1",
        "policy": {
            "scope": ["F", "H"],
            "automatic_selection": False,
            "master_changed": False,
            "harmony_changed": False,
            "runtime_changed": False,
            "product_assets_written": [],
        },
        "source": {**SOURCE, "characters": ["F", "H"]},
        "extraction": {
            "exif_orientation_applied_in_memory": True,
            "detection_threshold": DETECTION_THRESHOLD,
            "extraction_threshold": EXTRACTION_THRESHOLD,
            "component_relative_floor": .04,
            "dilation_kernel": [3, 3],
            "dilation_iterations": 1,
            "closing_kernel": [5, 5],
            "safe_margin": SAFE_MARGIN,
        },
        "totals": {"characters": 2, "candidates": 10, "F": 5, "H": 5},
        "characters": records,
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    verify_manifest(manifest)
    print("Imported exactly five new F and five new H repair candidates")
    return manifest


if __name__ == "__main__":
    import_sources()
