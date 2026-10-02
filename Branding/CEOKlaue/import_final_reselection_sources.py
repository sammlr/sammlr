#!/usr/bin/env python3
"""Append only the PO's nine final CEOKlaue reselection characters."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps


WORK = Path(__file__).resolve().parent
RAW = WORK / "00_raw"
EXTRACTED = WORK / "01_extracted" / "glyphs"
VECTORS = WORK / "02_vectors" / "glyphs"
MANIFEST = WORK / "final-reselection-source-manifest.json"
sys.path.insert(0, str(WORK / "03_font"))

from build_ceoklaue import archive_name, save_png, save_svg  # noqa: E402


SOURCE_SPECS = {
    "reselection_01": {
        "filename": "ceoklaue_final_reselection_01.jpg",
        "original_filename": "IMG_7174.JPG",
        "sha256": "77fd1bf51a10098fc0076a57f94583d686647b74fa65cfa6baf402b1a6f0f9a3",
        "pixel_dimensions": [4032, 3024],
        "oriented_dimensions": [3024, 4032],
        "x_range": [250, 2500],
        "rows": (
            ("H", (1150, 1550), 5),
            ("Z", (1680, 2070), 5),
            ("z", (2160, 2470), 5),
            ("x", (2540, 2850), 5),
        ),
    },
    "reselection_02": {
        "filename": "ceoklaue_final_reselection_02.jpg",
        "original_filename": "IMG_7175.JPG",
        "sha256": "a2794ad5ca03a08843ed38d8ebf455ee6ef523a621b8bd9b3ab3f8d357ec4018",
        "pixel_dimensions": [4032, 3024],
        "oriented_dimensions": [3024, 4032],
        "x_range": [250, 2550],
        "rows": (
            ("h", (930, 1360), 4),
            ("D", (1510, 1900), 5),
            ("F", (1980, 2390), 5),
            ("2", (2430, 2830), 5),
            ("ß", (2820, 3200), 5),
        ),
    },
}

OPEN_CHARACTERS = "HZzxhDF2ß"
DETECTION_THRESHOLD = 80
EXTRACTION_THRESHOLD = 90


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory_digest(paths) -> str:
    payload = "".join(
        f"{path.relative_to(WORK).as_posix()}\0{digest(path)}\n" for path in sorted(paths)
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def variant_ids(directory: Path, stem: str, suffix: str) -> list[int]:
    result = []
    if directory.is_dir():
        for path in directory.iterdir():
            match = re.fullmatch(rf"{re.escape(stem)}_(\d{{2}}){re.escape(suffix)}", path.name)
            if match:
                result.append(int(match.group(1)))
    return sorted(result)


def detect_horizontal_runs(gray, y0, y1, x0, x1):
    projection = (gray[y0:y1, x0:x1] < DETECTION_THRESHOLD).sum(axis=0)
    active = (projection > 3).astype(np.uint8)[None, :]
    active = cv2.morphologyEx(active, cv2.MORPH_CLOSE, np.ones((1, 50), np.uint8))[0]
    runs = []
    start = None
    for index, value in enumerate(active):
        if value and start is None:
            start = index
        if start is not None and (not value or index == len(active) - 1):
            end = index if not value else index + 1
            ink = int(projection[start:end].sum())
            if end - start > 8 and ink >= 2500:
                runs.append((start + x0, end + x0, ink))
            start = None
    return runs


def clean_mask(gray, box):
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
    pad = 6
    cropped = selected[y:y + height, x:x + width]
    return cv2.copyMakeBorder(
        cropped, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=0
    )


def verify_sources():
    for spec in SOURCE_SPECS.values():
        path = RAW / spec["filename"]
        if not path.is_file() or not path.stat().st_size:
            raise RuntimeError(f"Archived reselection source missing: {path}")
        if digest(path) != spec["sha256"]:
            raise RuntimeError(f"Archived reselection source changed: {path}")
        with Image.open(path) as image:
            if image.format != "JPEG" or list(image.size) != spec["pixel_dimensions"]:
                raise RuntimeError(f"Unexpected source format or dimensions: {path}")
            if list(ImageOps.exif_transpose(image).size) != spec["oriented_dimensions"]:
                raise RuntimeError(f"Unexpected oriented source dimensions: {path}")


def verify_existing_manifest(manifest):
    if manifest.get("version") != "CEOKlaue final glyph reselection source import v1":
        raise RuntimeError("Unknown final reselection manifest version")
    if manifest.get("open_characters") != OPEN_CHARACTERS:
        raise RuntimeError("Final reselection character scope changed")
    for source in manifest["sources"]:
        if digest(RAW / source["filename"]) != source["sha256"]:
            raise RuntimeError(f"Archived source changed: {source['filename']}")
    for record in manifest["characters"]:
        for output in record["outputs"]:
            for kind in ("png", "svg"):
                path = WORK / output[kind]["path"]
                if not path.is_file() or digest(path) != output[kind]["sha256"]:
                    raise RuntimeError(f"Reselection output changed or disappeared: {path}")


def import_sources():
    verify_sources()
    if MANIFEST.is_file():
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        verify_existing_manifest(manifest)
        print("CEOKlaue final reselection sources already imported and verified")
        return manifest

    preexisting_pngs = list(EXTRACTED.glob("*/*.png"))
    preexisting_svgs = list(VECTORS.glob("*/*.svg"))
    records = []
    with tempfile.TemporaryDirectory(prefix="ceoklaue-final-reselection-") as temporary:
        stage = Path(temporary)
        for source_key, spec in SOURCE_SPECS.items():
            source_path = RAW / spec["filename"]
            gray = np.asarray(ImageOps.exif_transpose(Image.open(source_path)).convert("L"))
            x0, x1 = spec["x_range"]
            for character, (y0, y1), expected_count in spec["rows"]:
                stem = archive_name(character)
                png_directory = EXTRACTED / stem
                svg_directory = VECTORS / stem
                png_ids = variant_ids(png_directory, stem, ".png")
                svg_ids = variant_ids(svg_directory, stem, ".svg")
                if png_ids != svg_ids:
                    raise RuntimeError(f"PNG/SVG inventory mismatch for {character}")
                first_new_id = (max(png_ids) if png_ids else 0) + 1
                new_ids = list(range(first_new_id, first_new_id + expected_count))
                detected = detect_horizontal_runs(gray, y0, y1, x0, x1)
                if len(detected) != expected_count:
                    raise RuntimeError(
                        f"Expected {expected_count} new sources for {character}, detected {detected}"
                    )
                outputs = []
                for new_id, (run_x0, run_x1, detected_ink) in zip(new_ids, detected):
                    filename = f"{stem}_{new_id:02d}"
                    target_png = png_directory / f"{filename}.png"
                    target_svg = svg_directory / f"{filename}.svg"
                    if target_png.exists() or target_svg.exists():
                        raise RuntimeError(f"Refusing to overwrite {filename}")
                    mask = clean_mask(
                        gray, (max(0, run_x0 - 45), y0, min(gray.shape[1], run_x1 + 45), y1)
                    )
                    staged_png = stage / "png" / stem / f"{filename}.png"
                    staged_svg = stage / "svg" / stem / f"{filename}.svg"
                    save_png(mask, staged_png)
                    save_svg(mask, staged_svg)
                    outputs.append({
                        "id": f"{new_id:02d}",
                        "detected_ink_pixels": detected_ink,
                        "mask_dimensions": [int(mask.shape[1]), int(mask.shape[0])],
                        "staged_png": staged_png,
                        "staged_svg": staged_svg,
                        "target_png": target_png,
                        "target_svg": target_svg,
                    })
                records.append({
                    "character": character,
                    "glyph_key": stem,
                    "source": spec["filename"],
                    "new_variant_ids": [output["id"] for output in outputs],
                    "outputs": outputs,
                })

        if "".join(record["character"] for record in records) != OPEN_CHARACTERS:
            raise RuntimeError("Final reselection import escaped its nine-character scope")
        if sum(len(record["outputs"]) for record in records) != 44:
            raise RuntimeError("Final reselection inventory must contain exactly 44 candidates")

        for record in records:
            for output in record["outputs"]:
                output["target_png"].parent.mkdir(parents=True, exist_ok=True)
                output["target_svg"].parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(output["staged_png"], output["target_png"])
                shutil.copy2(output["staged_svg"], output["target_svg"])
                output["png"] = {
                    "path": output["target_png"].relative_to(WORK).as_posix(),
                    "sha256": digest(output["target_png"]),
                }
                output["svg"] = {
                    "path": output["target_svg"].relative_to(WORK).as_posix(),
                    "sha256": digest(output["target_svg"]),
                }
                for transient in ("staged_png", "staged_svg", "target_png", "target_svg"):
                    del output[transient]

    manifest = {
        "version": "CEOKlaue final glyph reselection source import v1",
        "open_characters": OPEN_CHARACTERS,
        "policy": {
            "existing_variants_replaced": False,
            "accepted_triple_sets_changed": False,
            "automatic_selection": False,
            "harmony_font_built": False,
            "product_assets_written": [],
        },
        "sources": [
            {
                "key": source_key,
                "filename": spec["filename"],
                "original_filename": spec["original_filename"],
                "sha256": spec["sha256"],
                "pixel_dimensions": spec["pixel_dimensions"],
                "characters": "".join(row[0] for row in spec["rows"]),
            }
            for source_key, spec in SOURCE_SPECS.items()
        ],
        "extraction": {
            "exif_orientation_applied_in_memory": True,
            "detection_threshold": DETECTION_THRESHOLD,
            "extraction_threshold": EXTRACTION_THRESHOLD,
            "component_relative_floor": .04,
            "dilation_kernel": [3, 3],
            "dilation_iterations": 1,
            "closing_kernel": [5, 5],
        },
        "preexisting_inventory": {
            "png_count": len(preexisting_pngs),
            "svg_count": len(preexisting_svgs),
            "sha256": inventory_digest(preexisting_pngs + preexisting_svgs),
        },
        "totals": {
            "characters": len(records),
            "recognized_handwritten_sources": sum(len(record["outputs"]) for record in records),
            "extracted_pngs": sum(len(record["outputs"]) for record in records),
            "generated_svgs": sum(len(record["outputs"]) for record in records),
            "discarded_sources": 0,
        },
        "characters": records,
    }
    MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    verify_existing_manifest(manifest)
    print("Imported 44 real final-reselection candidates for exactly nine characters")
    return manifest


if __name__ == "__main__":
    import_sources()
