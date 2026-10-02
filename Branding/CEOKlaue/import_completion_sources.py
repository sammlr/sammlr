#!/usr/bin/env python3
"""Import the PO's final handwritten completion sheets without replacing data.

The three archived JPEGs remain untouched. Processing honors their EXIF
orientation in memory, segments exactly five real handwritten samples per
declared row and appends lossless PNG masks plus SVG contours to the existing
CEOKlaue work trees. Running the importer again verifies the completed import
instead of allocating duplicate variants.
"""

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
MANIFEST = WORK / "completion-source-manifest.json"
sys.path.insert(0, str(WORK / "03_font"))

from build_ceoklaue import archive_name, save_png, save_svg  # noqa: E402


SOURCE_SPECS = {
    "caps_lower": {
        "filename": "ceoklaue_completion_caps_lower_01.jpeg",
        "original_filename": "IMG_B8A9C787-DC21-4865-B2B1-C36BCD8B6ABF.jpeg",
        "sha256": "24b74b7fc4b3addc646452686977830a3525fa53450e548a716802d1a9a8f630",
        "pixel_dimensions": [4032, 3024],
        "oriented_dimensions": [3024, 4032],
        "x_range": [800, 1800],
        "minimum_detection_ink": 500,
        "rows": list(zip(
            list("GHJKLMNOPQRSUWek"),
            [
                (180, 315), (380, 540), (610, 790), (820, 1020),
                (1070, 1255), (1245, 1460), (1460, 1670), (1720, 1900),
                (1890, 2120), (2160, 2336), (2336, 2550), (2550, 2800),
                (2820, 3035), (3035, 3290), (3310, 3550), (3570, 3790),
            ],
        )),
    },
    "numbers_umlauts": {
        "filename": "ceoklaue_completion_numbers_umlauts_01.jpeg",
        "original_filename": "IMG_3EA29214-7F97-43A8-91DE-07692D5495DC.jpeg",
        "sha256": "202b5fa8201ab20775771db719516b85aaf6e6b54f6118941be9c61e134412c9",
        "pixel_dimensions": [4032, 3024],
        "oriented_dimensions": [3024, 4032],
        "x_range": [1600, 2750],
        "minimum_detection_ink": 1000,
        "rows": list(zip(
            ["0", "1", "3", "4", "6", "8", "ö", "ü", "Ä", "Ö", "Ü", "ß"],
            [
                (260, 470), (490, 710), (780, 1030), (1120, 1320),
                (1390, 1600), (1670, 1880), (1900, 2150), (2160, 2380),
                (2410, 2720), (2760, 3070), (3060, 3390), (3450, 3780),
            ],
        )),
    },
    "symbols": {
        "filename": "ceoklaue_completion_symbols_01.jpeg",
        "original_filename": "IMG_B2F41ED3-291D-4EEF-B533-0D6C2B91FBA9.jpeg",
        "sha256": "a9821df92b78a3cfc626efb489004549cfb25beb17ae918b539f02bd99f283f3",
        "pixel_dimensions": [4032, 3024],
        "oriented_dimensions": [3024, 4032],
        "x_range": [450, 2400],
        "minimum_detection_ink": 2000,
        "rows": list(zip(
            ["(", "&", "%", "?", ";"],
            [(620, 1080), (1090, 1610), (1720, 2140), (2130, 2690), (2750, 3200)],
        )),
    },
}

DETECTION_THRESHOLD = 80
EXTRACTION_THRESHOLD = 100
EXPECTED_VARIANTS_PER_CHARACTER = 5


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory_digest(paths) -> str:
    payload = "".join(
        f"{path.relative_to(WORK).as_posix()}\0{digest(path)}\n"
        for path in sorted(paths)
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


def detect_horizontal_runs(gray, y0, y1, x0, x1, minimum_ink):
    projection = (gray[y0:y1, x0:x1] < DETECTION_THRESHOLD).sum(axis=0)
    active = (projection > 3).astype(np.uint8)[None, :]
    active = cv2.morphologyEx(
        active, cv2.MORPH_CLOSE, np.ones((1, 45), np.uint8)
    )[0]
    runs = []
    start = None
    for index, value in enumerate(active):
        if value and start is None:
            start = index
        if start is not None and (not value or index == len(active) - 1):
            end = index if not value else index + 1
            ink = int(projection[start:end].sum())
            if end - start > 8 and ink >= minimum_ink:
                runs.append((start + x0, end + x0, ink))
            start = None
    return runs


def completion_mask(gray, box):
    x0, y0, x1, y1 = box
    mask = np.where(
        gray[y0:y1, x0:x1] < EXTRACTION_THRESHOLD, 255, 0
    ).astype(np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((2, 2), np.uint8))
    count, labels, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    areas = [int(stats[index, cv2.CC_STAT_AREA]) for index in range(1, count)]
    if areas:
        relative_floor = max(5, int(max(areas) * .05))
        selected = np.zeros_like(mask)
        for index, area in enumerate(areas, 1):
            if area >= relative_floor:
                selected[labels == index] = 255
        mask = selected
    mask = cv2.dilate(
        mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)), iterations=1
    )
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    points = cv2.findNonZero(mask)
    if points is None:
        raise RuntimeError(f"No handwritten ink found in completion crop {box}")
    x, y, width, height = cv2.boundingRect(points)
    pad = 3
    return cv2.copyMakeBorder(
        mask[
            max(0, y - pad):min(mask.shape[0], y + height + pad),
            max(0, x - pad):min(mask.shape[1], x + width + pad),
        ],
        pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=0,
    )


def verify_sources():
    for spec in SOURCE_SPECS.values():
        path = RAW / spec["filename"]
        if not path.is_file() or not path.stat().st_size:
            raise RuntimeError(f"Archived raw source is missing or unreadable: {path}")
        if digest(path) != spec["sha256"]:
            raise RuntimeError(f"Archived raw source bytes changed: {path}")
        with Image.open(path) as image:
            if image.format != "JPEG" or list(image.size) != spec["pixel_dimensions"]:
                raise RuntimeError(f"Unexpected JPEG format or dimensions: {path}")
            oriented = ImageOps.exif_transpose(image)
            if list(oriented.size) != spec["oriented_dimensions"]:
                raise RuntimeError(f"Unexpected oriented dimensions: {path}")


def verify_existing_manifest(manifest):
    if manifest.get("version") != "CEOKlaue final completion source import v1":
        raise RuntimeError("Unknown completion import manifest version")
    for source in manifest["sources"]:
        if digest(RAW / source["filename"]) != source["sha256"]:
            raise RuntimeError(f"Archived source changed after import: {source['filename']}")
    for record in manifest["characters"]:
        for output in record["outputs"]:
            for kind in ("png", "svg"):
                path = WORK / output[kind]["path"]
                if not path.is_file() or digest(path) != output[kind]["sha256"]:
                    raise RuntimeError(f"Completion output changed or disappeared: {path}")


def import_sources():
    verify_sources()
    if MANIFEST.is_file():
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        verify_existing_manifest(manifest)
        print("CEOKlaue completion sources already imported and verified")
        return manifest

    preexisting_pngs = list(EXTRACTED.rglob("*.png"))
    preexisting_svgs = list(VECTORS.rglob("*.svg"))
    records = []

    with tempfile.TemporaryDirectory(prefix="ceoklaue-completion-") as temporary:
        stage = Path(temporary)
        for source_key, spec in SOURCE_SPECS.items():
            source_path = RAW / spec["filename"]
            gray = np.array(ImageOps.exif_transpose(Image.open(source_path)).convert("L"))
            x0, x1 = spec["x_range"]
            for character, (y0, y1) in spec["rows"]:
                stem = archive_name(character)
                png_directory = EXTRACTED / stem
                svg_directory = VECTORS / stem
                png_ids = variant_ids(png_directory, stem, ".png")
                svg_ids = variant_ids(svg_directory, stem, ".svg")
                if png_ids != svg_ids:
                    raise RuntimeError(f"PNG/SVG variant inventory mismatch for {character}")
                new_ids = list(range((max(png_ids) if png_ids else 0) + 1,
                                     (max(png_ids) if png_ids else 0) + 6))
                detected = detect_horizontal_runs(
                    gray, y0, y1, x0, x1, spec["minimum_detection_ink"]
                )
                if len(detected) != EXPECTED_VARIANTS_PER_CHARACTER:
                    raise RuntimeError(
                        f"Expected five real sources for {character}, detected {detected}"
                    )
                outputs = []
                for new_id, (run_x0, run_x1, detected_ink) in zip(new_ids, detected):
                    filename = f"{stem}_{new_id:02d}"
                    target_png = png_directory / f"{filename}.png"
                    target_svg = svg_directory / f"{filename}.svg"
                    if target_png.exists() or target_svg.exists():
                        raise RuntimeError(f"Refusing to overwrite existing variant {filename}")
                    mask = completion_mask(
                        gray,
                        (max(0, run_x0 - 35), y0, min(gray.shape[1], run_x1 + 35), y1),
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
                    "recognized_handwritten_sources": len(detected),
                    "extracted_pngs": len(outputs),
                    "generated_svgs": len(outputs),
                    "new_variant_ids": [output["id"] for output in outputs],
                    "outputs": outputs,
                })

        if len(records) != 33 or sum(len(record["outputs"]) for record in records) != 165:
            raise RuntimeError("Completion import inventory is not exactly 33 × 5")

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

    sources = []
    for source_key, spec in SOURCE_SPECS.items():
        sources.append({
            "key": source_key,
            "filename": spec["filename"],
            "original_filename": spec["original_filename"],
            "sha256": spec["sha256"],
            "pixel_dimensions": spec["pixel_dimensions"],
            "characters": "".join(character for character, _row in spec["rows"]),
        })
    manifest = {
        "version": "CEOKlaue final completion source import v1",
        "policy": {
            "existing_variants_replaced": False,
            "automatic_triple_selection": False,
            "font_built": False,
            "discarded_sources": 0,
        },
        "sources": sources,
        "extraction": {
            "exif_orientation_applied_in_memory": True,
            "detection_threshold": DETECTION_THRESHOLD,
            "extraction_threshold": EXTRACTION_THRESHOLD,
            "component_relative_floor": .05,
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
            "recognized_handwritten_sources": sum(record["recognized_handwritten_sources"] for record in records),
            "extracted_pngs": sum(record["extracted_pngs"] for record in records),
            "generated_svgs": sum(record["generated_svgs"] for record in records),
            "discarded_sources": 0,
        },
        "characters": records,
    }
    MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    verify_existing_manifest(manifest)
    print("Imported 165 real completion glyphs as PNG and SVG for 33 characters")
    return manifest


if __name__ == "__main__":
    import_sources()
