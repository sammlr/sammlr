#!/usr/bin/env python3
"""Append the final six-glyph mini reselection and standalone selection marks."""

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
GLYPH_PNG = WORK / "01_extracted" / "glyphs"
GLYPH_SVG = WORK / "02_vectors" / "glyphs"
MARK_PNG = WORK / "01_extracted" / "selection_marks"
MARK_SVG = WORK / "02_vectors" / "selection_marks"
MANIFEST = WORK / "final-mini-reselection-source-manifest.json"
sys.path.insert(0, str(WORK / "03_font"))

from build_ceoklaue import archive_name, save_png, save_svg  # noqa: E402


SOURCE_SPECS = {
    "glyphs_01": {
        "filename": "ceoklaue_final_mini_reselection_glyphs_01.jpg",
        "original_filename": "IMG_7176.JPG",
        "sha256": "4558e07c32715f40da6ff301ba7eef14f3c866f53aaee44f6b4af6dc8521431f",
        "pixel_dimensions": [4032, 3024],
        "oriented_dimensions": [3024, 4032],
        "content": "font_glyph_candidates",
    },
    "marks_01": {
        "filename": "ceoklaue_final_mini_reselection_marks_01.jpg",
        "original_filename": "IMG_7177.JPG",
        "sha256": "b568ea40244c1a0852097837172ffbcb1e1bf4abf6ed2b8db15517cdab3bf9d7",
        "pixel_dimensions": [4032, 3024],
        "oriented_dimensions": [3024, 4032],
        "content": "selection_mark_candidates",
    },
}

GLYPH_ROWS = (
    ("v", (850, 1120)),
    ("w", (1280, 1600)),
    ("x", (1760, 2190)),
    ("V", (2200, 2620)),
    ("X", (2680, 3230)),
    (":", (3230, 3750)),
)
MARK_COLUMNS = {
    "receive_circle": {
        "x_range": (1650, 2350),
        "y_ranges": ((270, 900), (1000, 1580), (1700, 2260), (2450, 2950), (3000, 3600)),
    },
    "give_cross": {
        "x_range": (850, 1600),
        "y_ranges": ((300, 770), (1190, 1540), (1770, 2140), (2390, 2840), (3020, 3490)),
    },
}
OPEN_CHARACTERS = "vwxVX:"
DETECTION_THRESHOLD = 80
EXTRACTION_THRESHOLD = 90
SAFE_MARGIN = 6


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


def detect_horizontal_runs(gray, y0, y1, x0=250, x1=2500):
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
            if end - start > 8 and ink >= 1500:
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
    relative_floor = max(6, int(max(areas) * .035))
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
    cropped = selected[y:y + height, x:x + width]
    return cv2.copyMakeBorder(
        cropped, SAFE_MARGIN, SAFE_MARGIN, SAFE_MARGIN, SAFE_MARGIN,
        cv2.BORDER_CONSTANT, value=0,
    )


def verify_sources():
    for spec in SOURCE_SPECS.values():
        path = RAW / spec["filename"]
        if not path.is_file() or not path.stat().st_size:
            raise RuntimeError(f"Archived mini-reselection source missing: {path}")
        if digest(path) != spec["sha256"]:
            raise RuntimeError(f"Archived mini-reselection source changed: {path}")
        with Image.open(path) as image:
            # iPhone JPEGs with an auxiliary image are reported as MPO by Pillow.
            if image.format not in {"JPEG", "MPO"} or list(image.size) != spec["pixel_dimensions"]:
                raise RuntimeError(f"Unexpected source format or dimensions: {path}")
            if list(ImageOps.exif_transpose(image).size) != spec["oriented_dimensions"]:
                raise RuntimeError(f"Unexpected oriented source dimensions: {path}")


def verify_existing_manifest(manifest):
    if manifest.get("version") != "CEOKlaue final mini reselection source import v1":
        raise RuntimeError("Unknown final mini reselection manifest version")
    if manifest.get("open_characters") != OPEN_CHARACTERS:
        raise RuntimeError("Final mini reselection character scope changed")
    for source in manifest["sources"]:
        if digest(RAW / source["filename"]) != source["sha256"]:
            raise RuntimeError(f"Archived source changed: {source['filename']}")
    for group_name in ("characters", "selection_marks"):
        for record in manifest[group_name]:
            for output in record["outputs"]:
                for kind in ("png", "svg"):
                    path = WORK / output[kind]["path"]
                    if not path.is_file() or digest(path) != output[kind]["sha256"]:
                        raise RuntimeError(f"Mini-reselection output changed or disappeared: {path}")


def staged_output(stage, base_png, base_svg, stem, new_id, mask, detected_ink):
    filename = f"{stem}_{new_id:02d}"
    target_png = base_png / stem / f"{filename}.png"
    target_svg = base_svg / stem / f"{filename}.svg"
    if target_png.exists() or target_svg.exists():
        raise RuntimeError(f"Refusing to overwrite {filename}")
    staged_png = stage / "png" / stem / f"{filename}.png"
    staged_svg = stage / "svg" / stem / f"{filename}.svg"
    save_png(mask, staged_png)
    save_svg(mask, staged_svg)
    return {
        "id": f"{new_id:02d}",
        "detected_ink_pixels": int(detected_ink),
        "mask_dimensions": [int(mask.shape[1]), int(mask.shape[0])],
        "staged_png": staged_png,
        "staged_svg": staged_svg,
        "target_png": target_png,
        "target_svg": target_svg,
    }


def import_sources():
    verify_sources()
    if MANIFEST.is_file():
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        verify_existing_manifest(manifest)
        print("CEOKlaue final mini reselection sources already imported and verified")
        return manifest

    preexisting_pngs = sorted(GLYPH_PNG.glob("*/*.png"))
    preexisting_svgs = sorted(GLYPH_SVG.glob("*/*.svg"))
    preexisting = preexisting_pngs + preexisting_svgs
    character_records = []
    mark_records = []
    with tempfile.TemporaryDirectory(prefix="ceoklaue-final-mini-reselection-") as temporary:
        stage = Path(temporary)
        glyph_gray = np.asarray(
            ImageOps.exif_transpose(Image.open(RAW / SOURCE_SPECS["glyphs_01"]["filename"])).convert("L")
        )
        for character, (y0, y1) in GLYPH_ROWS:
            stem = archive_name(character)
            png_ids = variant_ids(GLYPH_PNG / stem, stem, ".png")
            svg_ids = variant_ids(GLYPH_SVG / stem, stem, ".svg")
            if png_ids != svg_ids:
                raise RuntimeError(f"PNG/SVG inventory mismatch for {character}")
            first_id = (max(png_ids) if png_ids else 0) + 1
            runs = detect_horizontal_runs(glyph_gray, y0, y1)
            if character == "x" and len(runs) == 6 and runs[0][0] == 250:
                runs = runs[1:]
            if len(runs) != 5:
                raise RuntimeError(f"Expected five new sources for {character}, detected {runs}")
            outputs = []
            for offset, (run_x0, run_x1, ink) in enumerate(runs):
                mask = clean_mask(
                    glyph_gray,
                    (max(0, run_x0 - 45), y0, min(glyph_gray.shape[1], run_x1 + 45), y1),
                )
                outputs.append(
                    staged_output(stage, GLYPH_PNG, GLYPH_SVG, stem, first_id + offset, mask, ink)
                )
            character_records.append({
                "character": character,
                "glyph_key": stem,
                "source": SOURCE_SPECS["glyphs_01"]["filename"],
                "source_mapping": {"oriented_y_range": [y0, y1], "reading_order": "left_to_right"},
                "new_variant_ids": [output["id"] for output in outputs],
                "outputs": outputs,
            })

        mark_gray = np.asarray(
            ImageOps.exif_transpose(Image.open(RAW / SOURCE_SPECS["marks_01"]["filename"])).convert("L")
        )
        for mark_key, spec in MARK_COLUMNS.items():
            png_ids = variant_ids(MARK_PNG / mark_key, mark_key, ".png")
            svg_ids = variant_ids(MARK_SVG / mark_key, mark_key, ".svg")
            if png_ids != svg_ids:
                raise RuntimeError(f"PNG/SVG inventory mismatch for {mark_key}")
            first_id = (max(png_ids) if png_ids else 0) + 1
            x0, x1 = spec["x_range"]
            outputs = []
            for offset, (y0, y1) in enumerate(spec["y_ranges"]):
                mask = clean_mask(mark_gray, (x0, y0, x1, y1))
                outputs.append(
                    staged_output(
                        stage, MARK_PNG, MARK_SVG, mark_key, first_id + offset,
                        mask, int((mark_gray[y0:y1, x0:x1] < DETECTION_THRESHOLD).sum()),
                    )
                )
            mark_records.append({
                "mark_key": mark_key,
                "source": SOURCE_SPECS["marks_01"]["filename"],
                "source_mapping": {
                    "oriented_x_range": list(spec["x_range"]),
                    "oriented_y_ranges": [list(item) for item in spec["y_ranges"]],
                    "reading_order": "top_to_bottom",
                },
                "new_variant_ids": [output["id"] for output in outputs],
                "outputs": outputs,
            })

        if "".join(record["character"] for record in character_records) != OPEN_CHARACTERS:
            raise RuntimeError("Final mini import escaped its six-character scope")
        if sum(len(record["outputs"]) for record in character_records) != 30:
            raise RuntimeError("Final mini glyph inventory must contain exactly 30 candidates")
        if sum(len(record["outputs"]) for record in mark_records) != 10:
            raise RuntimeError("Final mini marker inventory must contain exactly 10 candidates")

        for record in character_records + mark_records:
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
        "version": "CEOKlaue final mini reselection source import v1",
        "open_characters": OPEN_CHARACTERS,
        "marker_groups": ["receive_circle", "give_cross"],
        "policy": {
            "existing_variants_replaced": False,
            "accepted_triple_sets_changed": False,
            "automatic_selection": False,
            "harmony_assets_changed": False,
            "runtime_fonts_changed": False,
            "productive_sticker_assets_changed": False,
            "product_assets_written": [],
        },
        "sources": [
            {
                "key": key,
                "filename": spec["filename"],
                "original_filename": spec["original_filename"],
                "sha256": spec["sha256"],
                "format": "JPEG",
                "pixel_dimensions": spec["pixel_dimensions"],
                "oriented_dimensions": spec["oriented_dimensions"],
                "content": spec["content"],
            }
            for key, spec in SOURCE_SPECS.items()
        ],
        "extraction": {
            "exif_orientation_applied_in_memory": True,
            "detection_threshold": DETECTION_THRESHOLD,
            "extraction_threshold": EXTRACTION_THRESHOLD,
            "component_relative_floor": .035,
            "safe_transparent_margin_pixels": SAFE_MARGIN,
            "dilation_kernel": [3, 3],
            "dilation_iterations": 1,
            "closing_kernel": [5, 5],
        },
        "preexisting_inventory": {
            "png_count": len(preexisting_pngs),
            "svg_count": len(preexisting_svgs),
            "selection_mark_png_count": 0,
            "selection_mark_svg_count": 0,
            "sha256": inventory_digest(preexisting),
        },
        "totals": {
            "font_characters": 6,
            "font_glyph_candidates": 30,
            "selection_mark_groups": 2,
            "selection_mark_candidates": 10,
            "extracted_pngs": 40,
            "generated_svgs": 40,
            "discarded_sources": 0,
        },
        "characters": character_records,
        "selection_marks": mark_records,
    }
    MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    verify_existing_manifest(manifest)
    print("Imported 30 glyph and 10 selection-mark candidates without overwrites")
    return manifest


if __name__ == "__main__":
    import_sources()
