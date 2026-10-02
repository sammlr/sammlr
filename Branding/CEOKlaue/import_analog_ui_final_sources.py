#!/usr/bin/env python3
"""Append-only import for the final CEOKlaue analog-UI source drop."""

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
PROJECT = WORK.parents[1]
INBOX = WORK / "source-inbox"  # Optional local import input; never a machine-specific path.
RAW = WORK / "00_raw"
GLYPH_PNG = WORK / "01_extracted" / "glyphs"
GLYPH_SVG = WORK / "02_vectors" / "glyphs"
ANALOG_PNG = WORK / "01_extracted" / "analog_ui_final"
ANALOG_SVG = WORK / "02_vectors" / "analog_ui_final"
MANIFEST = WORK / "analog-ui-final-source-manifest.json"
sys.path.insert(0, str(WORK / "03_font"))

from build_ceoklaue import save_png, save_svg  # noqa: E402


SOURCE_SPECS = (
    ("analog_sheet", "ceoklaue_analog_ui_final_01.jpg", "IMG_7178.JPG", "499da63b20d435d1cb15aa0537d269add64e597854dc3820a5b41b971fcb2ed9"),
    ("u_detail", "ceoklaue_analog_ui_final_02.jpg", "IMG_7179.JPG", "c1953532155354337422769f81489e0b89f7ee3d432ecc10ce437b20aa311efc"),
    ("wordmark_sheet", "ceoklaue_analog_ui_final_03.jpg", "IMG_7180.JPG", "06bd6f9fb4907d61ef99ed3e561ac14a20aa9049f61b45cf4bec2352c578c958"),
    ("wordmark_detail", "ceoklaue_analog_ui_final_04.jpg", "IMG_7181.JPG", "33ee48f38b5a658a20f4d9582d14103892bc9794dc3da44a6675bd533eee96e5"),
    ("phrases_sheet", "ceoklaue_analog_ui_final_05.jpg", "IMG_7182.JPG", "47067a154ecc82b47e36379205dccd61e1cdeac512d0150c12c57acb64a2f754"),
    ("underlines_detail", "ceoklaue_analog_ui_final_06.jpg", "IMG_7183.JPG", "44686d072d1b32bf3e340c6c50cbbbc461c8facb90d79762201bc8890ff971fd"),
    ("boxes_lines_detail", "ceoklaue_analog_ui_final_07.jpg", "IMG_7184.JPG", "a99cc75dadf25c57e7437621d34ecd05245ce58539db66d5176d77f72cb73f19"),
)

SOURCE_FILE = {key: filename for key, filename, _original, _sha in SOURCE_SPECS}
SOURCE_BY_HASH = {sha: (key, filename, original) for key, filename, original, sha in SOURCE_SPECS}
THRESHOLD = 100
SAFE_MARGIN = 8

# Crops are in EXIF-oriented (3024 x 4032) source coordinates and preserve
# left-to-right/top-to-bottom source order. Detail photos are preferred where
# the same physical drawing occurs in more than one photograph.
SELECTION_CROPS = (
    ("u", "lower_u", "u_detail", (
        (320, 1330, 590, 1700), (700, 1330, 1000, 1700),
        (1120, 1330, 1400, 1700), (1570, 1330, 1850, 1700),
        (1980, 1330, 2250, 1700),
    )),
    ("A", "cap_A", "analog_sheet", (
        (330, 2630, 590, 2980), (620, 2630, 840, 2980),
        (850, 2630, 1080, 2980), (1090, 2630, 1360, 2980),
        (1380, 2630, 1700, 2980),
    )),
    (",", "comma", "analog_sheet", (
        (500, 1240, 650, 1460), (810, 1240, 950, 1460),
        (1130, 1240, 1280, 1460), (1440, 1240, 1600, 1460),
        (1750, 1240, 1930, 1460),
    )),
)

ANALOG_GROUPS = (
    ("middle_dot", "analog_sheet", (
        (500, 1600, 650, 1790), (810, 1600, 950, 1790),
        (1130, 1600, 1280, 1790), (1430, 1600, 1580, 1790),
        (1740, 1600, 1940, 1790),
    )),
    # The large first arrow is the single final arrow on the source row.
    ("back_arrow", "analog_sheet", (
        (420, 1900, 690, 2160),
        (735, 1900, 1005, 2160),
        (1045, 1900, 1315, 2160),
        (1355, 1900, 1625, 2160),
        (1665, 1900, 1935, 2160),
    )),
    # One connected master from the sharp detail photo; never split into glyphs.
    ("wordmark_sammlr", "wordmark_detail", ((70, 1050, 2670, 1660),)),
    ("phrase_aktueller_tausch", "phrases_sheet", (
        (250, 400, 2110, 760), (280, 780, 2050, 1060), (270, 1070, 2050, 1410),
    )),
    ("phrase_du_gibst_ab", "phrases_sheet", (
        (300, 1410, 1770, 1710), (340, 1730, 1790, 2040),
    )),
    ("phrase_mehr_ellipsis", "phrases_sheet", (
        (410, 2030, 1120, 2310), (1380, 2030, 2060, 2310), (2110, 2000, 2780, 2310),
    )),
    ("phrase_auswahl_pruefen", "phrases_sheet", (
        (420, 2290, 1980, 2630), (450, 2620, 1900, 2920),
    )),
    ("underline", "underlines_detail", (
        (900, 1080, 2070, 1210), (850, 1260, 2080, 1420),
        (850, 1590, 2110, 1750), (850, 1860, 2140, 2040),
        (830, 2180, 1480, 2320), (180, 2430, 2220, 2620),
    )),
    ("box", "boxes_lines_detail", (
        (220, 740, 920, 1080), (1080, 800, 1960, 1160),
        (230, 1130, 1210, 1470), (1220, 1150, 2090, 1530),
        (270, 1530, 1160, 1940), (1220, 1540, 2050, 1960),
    )),
    ("line_component_vertical", "boxes_lines_detail", (
        (1230, 2140, 1380, 2470), (1230, 2490, 1380, 2790),
        (1230, 2810, 1380, 3130), (1230, 3150, 1400, 3480),
        (1660, 3260, 1800, 3510), (1870, 3240, 2020, 3520),
    )),
    ("line_component_horizontal", "boxes_lines_detail", (
        (1430, 2110, 2440, 2280), (1460, 2320, 2100, 2480),
        (1430, 2460, 2860, 2690), (1460, 2700, 2290, 2880),
        (1460, 2910, 2100, 3060), (1430, 3060, 2450, 3250),
    )),
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory_digest(paths) -> str:
    payload = "".join(
        f"{path.relative_to(WORK).as_posix()}\0{digest(path)}\n" for path in sorted(paths)
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def variant_ids(directory: Path, stem: str, suffix: str) -> list[int]:
    ids = []
    if directory.is_dir():
        for path in directory.iterdir():
            match = re.fullmatch(rf"{re.escape(stem)}_(\d{{2}}){re.escape(suffix)}", path.name)
            if match:
                ids.append(int(match.group(1)))
    return sorted(ids)


def locate_sources() -> dict[str, Path]:
    found = {}
    for path in INBOX.iterdir():
        if not path.is_file():
            continue
        sha = digest(path)
        if sha in SOURCE_BY_HASH:
            key, _archive, _original = SOURCE_BY_HASH[sha]
            found[key] = path
    expected = {key for key, *_rest in SOURCE_SPECS}
    if set(found) != expected:
        raise RuntimeError(f"Expected source hashes {sorted(expected)}, found {sorted(found)}")
    return found


def archive_sources() -> None:
    located = locate_sources()
    RAW.mkdir(parents=True, exist_ok=True)
    for key, filename, _original, sha in SOURCE_SPECS:
        target = RAW / filename
        if target.exists():
            if digest(target) != sha:
                raise RuntimeError(f"Refusing to overwrite changed raw source: {target}")
            continue
        shutil.copy2(located[key], target)
        if digest(target) != sha:
            raise RuntimeError(f"Byte-exact archive verification failed: {target}")


def source_gray(key: str) -> np.ndarray:
    image = Image.open(RAW / SOURCE_FILE[key])
    if image.format not in {"JPEG", "MPO"} or image.size != (4032, 3024):
        raise RuntimeError(f"Unexpected source format/dimensions: {SOURCE_FILE[key]}")
    oriented = ImageOps.exif_transpose(image)
    if oriented.size != (3024, 4032):
        raise RuntimeError(f"Unexpected oriented dimensions: {SOURCE_FILE[key]}")
    return np.asarray(oriented.convert("L"))


def clean_crop(gray: np.ndarray, box: tuple[int, int, int, int]) -> np.ndarray:
    x0, y0, x1, y1 = box
    mask = np.where(gray[y0:y1, x0:x1] < THRESHOLD, 255, 0).astype(np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((2, 2), np.uint8))
    count, labels, stats, _centroids = cv2.connectedComponentsWithStats(mask, 8)
    cleaned = np.zeros_like(mask)
    for index in range(1, count):
        _x, _y, width, height, area = stats[index]
        if area < 18:
            continue
        if width > mask.shape[1] * .94 and height <= 3:
            continue
        if height > mask.shape[0] * .94 and width <= 3:
            continue
        cleaned[labels == index] = 255
    points = cv2.findNonZero(cleaned)
    if points is None:
        raise RuntimeError(f"No handwritten ink in crop {box}")
    x, y, width, height = cv2.boundingRect(points)
    cropped = cleaned[y:y + height, x:x + width]
    return cv2.copyMakeBorder(
        cropped, SAFE_MARGIN, SAFE_MARGIN, SAFE_MARGIN, SAFE_MARGIN,
        cv2.BORDER_CONSTANT, value=0,
    )


def stage_output(stage: Path, target_png: Path, target_svg: Path, mask: np.ndarray) -> dict:
    if target_png.exists() or target_svg.exists():
        raise RuntimeError(f"Refusing to overwrite existing asset: {target_png.stem}")
    relative = target_png.relative_to(WORK)
    staged_png = stage / relative
    staged_svg = stage / target_svg.relative_to(WORK)
    save_png(mask, staged_png)
    save_svg(mask, staged_svg)
    return {
        "mask_dimensions": [int(mask.shape[1]), int(mask.shape[0])],
        "staged_png": staged_png,
        "staged_svg": staged_svg,
        "target_png": target_png,
        "target_svg": target_svg,
    }


def finalize_output(output: dict) -> None:
    for staged_key, target_key in (("staged_png", "target_png"), ("staged_svg", "target_svg")):
        staged, target = output[staged_key], output[target_key]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(staged, target)
    output["png"] = {
        "path": output["target_png"].relative_to(WORK).as_posix(),
        "sha256": digest(output["target_png"]),
    }
    output["svg"] = {
        "path": output["target_svg"].relative_to(WORK).as_posix(),
        "sha256": digest(output["target_svg"]),
    }
    for key in ("staged_png", "staged_svg", "target_png", "target_svg"):
        del output[key]


def verify_manifest(manifest: dict) -> None:
    if manifest.get("version") != "CEOKlaue analog UI final source import v1":
        raise RuntimeError("Unknown analog UI manifest version")
    for source in manifest["sources"]:
        path = RAW / source["filename"]
        if not path.is_file() or digest(path) != source["sha256"]:
            raise RuntimeError(f"Archived analog source changed: {path}")
    for record in manifest["selection_groups"] + manifest["fixed_assets"]:
        for output in record["outputs"]:
            for kind in ("png", "svg"):
                path = WORK / output[kind]["path"]
                if not path.is_file() or digest(path) != output[kind]["sha256"]:
                    raise RuntimeError(f"Analog output changed: {path}")


def upgrade_back_arrow_inventory(manifest: dict) -> dict:
    """Complete the five real arrows already present on the archived analog sheet."""
    record = next(item for item in manifest["fixed_assets"] if item["asset_key"] == "back_arrow")
    if len(record["outputs"]) == 5:
        return manifest
    if len(record["outputs"]) != 1:
        raise RuntimeError("Unexpected partial back-arrow inventory")
    gray = source_gray("analog_sheet")
    boxes = next(boxes for key, _source, boxes in ANALOG_GROUPS if key == "back_arrow")
    for index, box in enumerate(boxes[1:], 2):
        stem = f"back_arrow_{index:02d}"
        png = ANALOG_PNG / "back_arrow" / f"{stem}.png"
        svg = ANALOG_SVG / "back_arrow" / f"{stem}.svg"
        mask = clean_crop(gray, box)
        png.parent.mkdir(parents=True, exist_ok=True)
        svg.parent.mkdir(parents=True, exist_ok=True)
        save_png(mask, png)
        save_svg(mask, svg)
        record["outputs"].append({
            "mask_dimensions": [int(mask.shape[1]), int(mask.shape[0])],
            "id": f"{index:02d}",
            "source_region_id": f"back_arrow-{index:02d}",
            "oriented_crop": list(box),
            "png": {"path": png.relative_to(WORK).as_posix(), "sha256": digest(png)},
            "svg": {"path": svg.relative_to(WORK).as_posix(), "sha256": digest(svg)},
        })
    manifest["totals"]["back_arrows"] = 5
    manifest["totals"]["extracted_pngs"] += 4
    manifest["totals"]["generated_svgs"] += 4
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def import_sources() -> dict:
    if MANIFEST.is_file():
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        manifest = upgrade_back_arrow_inventory(manifest)
        verify_manifest(manifest)
        print("CEOKlaue analog UI final sources already imported and verified")
        return manifest

    archive_sources()
    preexisting = sorted(GLYPH_PNG.glob("*/*.png")) + sorted(GLYPH_SVG.glob("*/*.svg"))
    images = {key: source_gray(key) for key, *_rest in SOURCE_SPECS}
    selection_records = []
    fixed_records = []
    all_outputs = []
    with tempfile.TemporaryDirectory(prefix="ceoklaue-analog-ui-final-") as temporary:
        stage = Path(temporary)
        for character, key, source_key, boxes in SELECTION_CROPS:
            png_ids = variant_ids(GLYPH_PNG / key, key, ".png")
            svg_ids = variant_ids(GLYPH_SVG / key, key, ".svg")
            if png_ids != svg_ids:
                raise RuntimeError(f"PNG/SVG inventory mismatch for {key}")
            first = max(png_ids, default=0) + 1
            outputs = []
            for offset, box in enumerate(boxes):
                variant = first + offset
                filename = f"{key}_{variant:02d}"
                output = stage_output(
                    stage,
                    GLYPH_PNG / key / f"{filename}.png",
                    GLYPH_SVG / key / f"{filename}.svg",
                    clean_crop(images[source_key], box),
                )
                output.update({"id": f"{variant:02d}", "source_region_id": f"{key}-{offset + 1:02d}", "oriented_crop": list(box)})
                outputs.append(output)
            selection_records.append({
                "selection_key": character,
                "asset_key": key,
                "source": SOURCE_FILE[source_key],
                "required_selection": {"min": 3, "max": 3},
                "new_variant_ids": [output["id"] for output in outputs],
                "outputs": outputs,
            })
            all_outputs.extend(outputs)

        # The fifth 2 is immediately identified by the handwritten 2_1 note.
        # It is fixed preview inventory, but its variant number still continues
        # the existing glyph family instead of introducing a parallel key.
        key = "2"
        png_ids = variant_ids(GLYPH_PNG / key, key, ".png")
        svg_ids = variant_ids(GLYPH_SVG / key, key, ".svg")
        if png_ids != svg_ids:
            raise RuntimeError("PNG/SVG inventory mismatch for digit 2")
        variant = max(png_ids, default=0) + 1
        box = (1750, 2980, 2150, 3330)
        output = stage_output(
            stage,
            GLYPH_PNG / key / f"{key}_{variant:02d}.png",
            GLYPH_SVG / key / f"{key}_{variant:02d}.svg",
            clean_crop(images["analog_sheet"], box),
        )
        output.update({
            "id": f"{variant:02d}",
            "source_region_id": "digit_2_replacement_alt1-01",
            "oriented_crop": list(box),
        })
        fixed_records.append({
            "asset_key": key,
            "inventory_key": "digit_2_replacement_alt1",
            "source": SOURCE_FILE["analog_sheet"],
            "new_variant_ids": [output["id"]],
            "outputs": [output],
        })
        all_outputs.append(output)

        for key, source_key, boxes in ANALOG_GROUPS:
            outputs = []
            for index, box in enumerate(boxes, 1):
                filename = f"{key}_{index:02d}"
                output = stage_output(
                    stage,
                    ANALOG_PNG / key / f"{filename}.png",
                    ANALOG_SVG / key / f"{filename}.svg",
                    clean_crop(images[source_key], box),
                )
                output.update({"id": f"{index:02d}", "source_region_id": f"{key}-{index:02d}", "oriented_crop": list(box)})
                outputs.append(output)
            record = {
                "asset_key": key,
                "source": SOURCE_FILE[source_key],
                "outputs": outputs,
            }
            if key == "middle_dot":
                record.update({
                    "selection_key": "middle_dot",
                    "required_selection": {"min": 1, "max": min(3, len(outputs))},
                    "new_variant_ids": [output["id"] for output in outputs],
                })
                selection_records.append(record)
            else:
                fixed_records.append(record)
            all_outputs.extend(outputs)

        for output in all_outputs:
            finalize_output(output)

    # The replacement is fixed preview inventory, not a selection group.
    totals = {
        "new_u_candidates": 5,
        "new_A_candidates": 5,
        "new_comma_candidates": 5,
        "new_middle_dot_candidates": 5,
        "digit_2_replacements": 1,
        "back_arrows": 5,
        "wordmarks": 1,
        "phrase_assets": 10,
        "underlines": 6,
        "boxes": 6,
        "line_components": 12,
        "extracted_pngs": len(all_outputs),
        "generated_svgs": len(all_outputs),
    }
    manifest = {
        "version": "CEOKlaue analog UI final source import v1",
        "drop": "analog_ui_final",
        "policy": {
            "append_only": True,
            "automatic_selection": False,
            "product_integration": False,
            "accepted_82x3_masterset_changed": False,
            "harmony_changed": False,
            "runtime_changed": False,
            "sticker_list_changed": False,
            "sticker_wall_changed": False,
            "product_assets_written": [],
        },
        "sources": [
            {
                "key": key,
                "filename": filename,
                "original_filename": original,
                "format": "JPEG",
                "pixel_dimensions": [4032, 3024],
                "oriented_dimensions": [3024, 4032],
                "sha256": sha,
            }
            for key, filename, original, sha in SOURCE_SPECS
        ],
        "extraction": {
            "exif_orientation_applied_in_memory": True,
            "threshold": THRESHOLD,
            "safe_transparent_margin_pixels": SAFE_MARGIN,
            "physical_marks_deduplicated_across_detail_photos": True,
            "geometry_correction": False,
            "synthetic_assets": False,
        },
        "preexisting_glyph_inventory": {
            "png_count": len(list(GLYPH_PNG.glob("*/*.png"))) - 15,
            "svg_count": len(list(GLYPH_SVG.glob("*/*.svg"))) - 15,
            "sha256": inventory_digest(preexisting),
        },
        "selection_groups": selection_records,
        "fixed_assets": fixed_records,
        "not_found_in_new_sources": ["phrase_du_bekommst", "phrase_mehr_anzeigen"],
        "totals": totals,
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    verify_manifest(manifest)
    print(f"Imported {len(all_outputs)} analog UI assets without overwrites")
    return manifest


if __name__ == "__main__":
    import_sources()
