#!/usr/bin/env python3
"""Build private, deterministic Harmony Preview SVGs from the PO's triples.

The archived PNG masks remain untouched.  Every selected source is normalized
onto a shared visual em, then receives only a bounded topology-preserving
stroke-density correction.  The output is exclusively consumed by the
development/testing Harmony Preview.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[3]
WORK = ROOT / "Branding" / "CEOKlaue"
EXTRACTED = WORK / "01_extracted" / "glyphs"
FINAL_FH_REPAIR_EXTRACTED = WORK / "01_extracted" / "final_fh_repair"
MARK_EXTRACTED = WORK / "01_extracted" / "selection_marks"
OUTPUT = WORK / "04_harmony" / "glyphs"
MARK_OUTPUT = WORK / "04_harmony" / "selection_marks"
MANIFEST = WORK / "04_harmony" / "manifest.json"
sys.path.insert(0, str(WORK / "03_font"))

from build_ceoklaue import archive_name  # noqa: E402


CHARACTER_ROWS = (
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
    "abcdefghijklmnopqrstuvwxyz",
    "0123456789",
    "äöüÄÖÜß",
    ".,:;!?-+/&%()",
)
CHARACTER_ORDER = "".join(CHARACTER_ROWS)
SELECTIONS = {
    "A": ("07", "08", "09"), "B": ("05", "01", "03"),
    "C": ("01", "03", "02"), "D": ("09", "01", "05"),
    "E": ("03", "05", "01"), "F": ("05", "02", "01"),
    "G": ("01", "09", "07"), "H": ("01", "04", "05"),
    "I": ("01", "02", "04"), "J": ("10", "07", "06"),
    "K": ("06", "08", "07"), "L": ("07", "06", "09"),
    "M": ("03", "06", "07"), "N": ("03", "08", "07"),
    "O": ("07", "08", "10"), "P": ("06", "08", "09"),
    "Q": ("07", "10", "08"), "R": ("06", "07", "08"),
    "S": ("06", "09", "08"), "T": ("02", "01", "03"),
    "U": ("04", "01", "08"), "V": ("07", "09", "10"),
    "W": ("06", "08", "09"), "X": ("06", "09", "10"),
    "Y": ("03", "01", "04"), "Z": ("08", "09", "10"),
    "a": ("03", "02", "04"), "b": ("05", "04", "02"),
    "c": ("04", "02", "03"), "d": ("02", "01", "04"),
    "e": ("01", "08", "10"), "f": ("05", "03", "02"),
    "g": ("03", "02", "01"), "h": ("05", "01", "08"),
    "i": ("04", "03", "05"), "j": ("05", "01", "02"),
    "k": ("06", "09", "08"), "l": ("03", "04", "05"),
    "m": ("02", "01", "04"), "n": ("05", "01", "03"),
    "o": ("04", "01", "02"), "p": ("02", "01", "05"),
    "q": ("05", "01", "04"), "r": ("03", "01", "05"),
    "s": ("03", "02", "05"), "t": ("04", "01", "02"),
    "u": ("06", "08", "10"), "v": ("07", "09", "08"),
    "w": ("08", "10", "09"), "x": ("12", "11", "13"),
    "y": ("02", "03", "01"), "z": ("07", "08", "10"),
    "0": ("06", "09", "08"), "1": ("01", "07", "09"),
    "2": ("11", "09", "10"), "3": ("01", "07", "09"),
    "4": ("02", "07", "06"), "5": ("02", "01", "03"),
    "6": ("07", "08", "10"), "7": ("05", "03", "01"),
    "8": ("03", "06", "10"), "9": ("05", "01", "02"),
    "ä": ("04", "03", "05"), "ö": ("07", "08", "09"),
    "ü": ("06", "08", "07"), "Ä": ("04", "01", "03"),
    "Ö": ("02", "05", "03"), "Ü": ("02", "04", "05"),
    "ß": ("12", "13", "14"), ".": ("03", "05", "02"),
    ",": ("06", "08", "09"), ":": ("07", "09", "10"),
    ";": ("03", "04", "02"), "!": ("05", "04", "01"),
    "?": ("07", "06", "09"), "-": ("04", "03", "02"),
    "+": ("02", "04", "03"), "/": ("03", "01", "04"),
    "&": ("06", "08", "09"), "%": ("06", "07", "08"),
    "(": ("06", "07", "09"), ")": ("04", "01", "02"),
}

CANVAS_HEIGHT = 1000
SIDE_BEARING = 55
MAX_MORPHOLOGY_STEPS = 8
MARKER_SELECTIONS = {
    "receive_circle": ("01", "02", "04", "03", "05"),
    "give_cross": ("05", "03", "04", "01", "02"),
}
MARKER_ROTATION_DEGREES = -90
MARKER_CANVAS = (1000, 620)
MARKER_SAFE_MARGIN = 60

# Keep the established class corridors locked so final local F/H replacements
# cannot silently re-harmonize unrelated glyphs.
LOCKED_CLASS_TARGETS = {
    "capitals": 41.181,
    "lowercase": 48.0,
    "digits": 42.969,
    "mark-002e": 37.5625,
    "mark-002c": 18.0,
    "mark-003a": 46.738,
    "structural-punctuation": 36.787,
    "mark-002d": 126.0,
}
LOCKED_CHARACTER_DENSITY_MEDIANS = {}
FINAL_FH_REPAIR_SELECTIONS = {
    "F": {"05": "cap_F_new_05.png", "02": "cap_F_new_02.png", "01": "cap_F_new_01.png"},
    "H": {"01": "cap_H_new_01.png", "04": "cap_H_new_04.png", "05": "cap_H_new_05.png"},
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_path(character: str, variant: str) -> Path:
    if character in FINAL_FH_REPAIR_SELECTIONS:
        filename = FINAL_FH_REPAIR_SELECTIONS[character].get(variant)
        if filename is None:
            raise RuntimeError(f"Unapproved final F/H repair selection {character}={variant}")
        return FINAL_FH_REPAIR_EXTRACTED / filename
    key = archive_name(character)
    return EXTRACTED / key / f"{key}_{variant}.png"


def visible_geometry(character: str) -> tuple[int, int]:
    if character in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        return 620, 150
    if character in "ÄÖÜ":
        return 650, 120
    if character in "gjpqy":
        return 600, 300
    if character == "j":
        return 650, 250
    if character in "bdfhkltß":
        return 580, 190
    if character in "i":
        return 510, 260
    if character in "äöü":
        return 540, 230
    if character in "abcdefghijklmnopqrstuvwxyz":
        return 430, 340
    if character.isdigit():
        return 590, 180
    return {
        ".": (70, 700), ",": (140, 700), ":": (280, 420),
        ";": (360, 420), "!": (600, 170), "?": (600, 170),
        "-": (80, 500), "+": (300, 380), "/": (650, 140),
        "&": (620, 160), "%": (620, 160), "(": (620, 160),
        ")": (620, 160),
    }[character]


def stroke_class(character: str) -> str:
    if character in "ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÜ":
        return "capitals"
    if character in "abcdefghijklmnopqrstuvwxyzäöüß":
        return "lowercase"
    if character.isdigit():
        return "digits"
    if character in ".,:-":
        return f"mark-{ord(character):04x}"
    return "structural-punctuation"


def target_corridor(character: str, class_targets: dict[str, float]) -> tuple[float, float]:
    target = class_targets[stroke_class(character)]
    if character in ".,:-":
        return target * .88, target * 1.12
    return max(28.0, target - 4.0), target + 4.0


def load_normalized(character: str, variant: str) -> tuple[np.ndarray, Path]:
    path = source_path(character, variant)
    if not path.is_file():
        raise RuntimeError(f"Missing selected source {character}={variant}: {path}")
    alpha = np.asarray(Image.open(path).convert("RGBA"))[:, :, 3]
    points = cv2.findNonZero(np.where(alpha > 127, 255, 0).astype(np.uint8))
    if points is None:
        raise RuntimeError(f"Selected source has no ink: {path}")
    x, y, width, height = cv2.boundingRect(points)
    cropped = alpha[y:y + height, x:x + width]
    target_height, _top = visible_geometry(character)
    target_width = max(1, round(width * target_height / height))
    normalized = cv2.resize(
        np.where(cropped > 127, 255, 0).astype(np.uint8),
        (target_width, target_height),
        interpolation=cv2.INTER_NEAREST,
    )
    return normalized, path


def topology(mask: np.ndarray) -> tuple[int, int]:
    components, _labels = cv2.connectedComponents((mask > 0).astype(np.uint8), 8)
    _contours, hierarchy = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    holes = 0 if hierarchy is None else sum(1 for node in hierarchy[0] if node[3] != -1)
    return components - 1, holes


def thickness(mask: np.ndarray) -> float:
    distance = cv2.distanceTransform((mask > 0).astype(np.uint8), cv2.DIST_L2, 5)
    values = distance[distance > 0]
    return float(np.percentile(values, 90) * 2) if len(values) else 0.0


def ink_density(mask: np.ndarray) -> float:
    return float(np.count_nonzero(mask) / mask.size)


def harmonize_stroke(
    mask: np.ndarray,
    corridor: tuple[float, float],
    character_density_median: float,
) -> tuple[np.ndarray, dict]:
    original_topology = topology(mask)
    before_thickness = thickness(mask)
    before_density = ink_density(mask)
    low, high = corridor
    operation = "none"
    if before_thickness < low and before_density <= character_density_median * 1.18:
        operation = "dilate"
    elif before_thickness > high and before_density >= character_density_median * .82:
        operation = "erode"

    result = mask.copy()
    steps = 0
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    for _attempt in range(MAX_MORPHOLOGY_STEPS):
        measured = thickness(result)
        if operation == "none" or (low <= measured <= high):
            break
        candidate = (
            cv2.dilate(result, kernel, iterations=1)
            if operation == "dilate"
            else cv2.erode(result, kernel, iterations=1)
        )
        if not np.count_nonzero(candidate) or topology(candidate) != original_topology:
            break
        result = candidate
        steps += 1

    return result, {
        "measurement": "90th percentile of normalized distance-transform diameter",
        "ink_density_considered": True,
        "stroke_class_corridor": [round(low, 3), round(high, 3)],
        "thickness_before": round(before_thickness, 3),
        "thickness_after": round(thickness(result), 3),
        "ink_density_before": round(before_density, 6),
        "ink_density_after": round(ink_density(result), 6),
        "operation": operation if steps else "none",
        "steps": steps,
        "topology_before": {"components": original_topology[0], "holes": original_topology[1]},
        "topology_after": {"components": topology(result)[0], "holes": topology(result)[1]},
    }


def svg_source(mask: np.ndarray, character: str) -> tuple[str, int]:
    contours, _hierarchy = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        raise RuntimeError(f"No contours after Harmony normalization for {character}")
    target_height, top = visible_geometry(character)
    width = mask.shape[1]
    advance = max(160, width + 2 * SIDE_BEARING)
    commands = []
    for contour in contours:
        points = contour[:, 0, :]
        if len(points) < 3:
            continue
        commands.append(f"M {int(points[0][0] + SIDE_BEARING)} {int(points[0][1] + top)}")
        commands.extend(
            f"L {int(x + SIDE_BEARING)} {int(y + top)}" for x, y in points[1:]
        )
        commands.append("Z")
    path_data = " ".join(commands)
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {advance} {CANVAS_HEIGHT}" width="{advance}" height="{CANVAS_HEIGHT}">'
        f'<path d="{path_data}" fill="#211d22" fill-rule="evenodd"/></svg>\n'
    )
    return svg, advance


def marker_source_path(family: str, variant: str) -> Path:
    return MARK_EXTRACTED / family / f"{family}_{variant}.png"


def load_rotated_marker(family: str, variant: str) -> tuple[np.ndarray, Path]:
    path = marker_source_path(family, variant)
    if not path.is_file():
        raise RuntimeError(f"Missing selected marker {family}={variant}: {path}")
    alpha = np.asarray(Image.open(path).convert("RGBA"))[:, :, 3]
    binary = np.where(alpha > 127, 255, 0).astype(np.uint8)
    # Binding PO instruction: every marker, without exception, rotates 90° left.
    rotated = cv2.rotate(binary, cv2.ROTATE_90_COUNTERCLOCKWISE)
    points = cv2.findNonZero(rotated)
    if points is None:
        raise RuntimeError(f"Selected marker has no ink: {path}")
    x, y, width, height = cv2.boundingRect(points)
    cropped = rotated[y:y + height, x:x + width]
    max_width = MARKER_CANVAS[0] - 2 * MARKER_SAFE_MARGIN
    max_height = MARKER_CANVAS[1] - 2 * MARKER_SAFE_MARGIN
    scale = min(max_width / width, max_height / height)
    normalized = cv2.resize(
        cropped,
        (max(1, round(width * scale)), max(1, round(height * scale))),
        interpolation=cv2.INTER_NEAREST,
    )
    return normalized, path


def marker_svg_source(mask: np.ndarray, family: str) -> str:
    contours, _hierarchy = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        raise RuntimeError(f"No contours after marker harmonization for {family}")
    canvas_width, canvas_height = MARKER_CANVAS
    offset_x = (canvas_width - mask.shape[1]) // 2
    offset_y = (canvas_height - mask.shape[0]) // 2
    commands = []
    for contour in contours:
        points = contour[:, 0, :]
        if len(points) < 3:
            continue
        commands.append(f"M {int(points[0][0] + offset_x)} {int(points[0][1] + offset_y)}")
        commands.extend(
            f"L {int(x + offset_x)} {int(y + offset_y)}" for x, y in points[1:]
        )
        commands.append("Z")
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {canvas_width} {canvas_height}" width="{canvas_width}" height="{canvas_height}" '
        f'data-marker-family="{family}" data-rotation-degrees="{MARKER_ROTATION_DEGREES}">'
        f'<path d="{" ".join(commands)}" fill="#211d22" fill-rule="evenodd"/></svg>\n'
    )


def build_markers() -> tuple[list[dict], list[Path], dict]:
    if set(MARKER_SELECTIONS) != {"receive_circle", "give_cross"}:
        raise RuntimeError("Final marker scope must contain receive_circle and give_cross")
    if any(len(variants) != 5 or len(set(variants)) != 5 for variants in MARKER_SELECTIONS.values()):
        raise RuntimeError("Each final marker family needs five distinct selected variants")

    prepared = {}
    measured = []
    family_densities: dict[str, list[float]] = {}
    for family, variants in MARKER_SELECTIONS.items():
        for variant in variants:
            mask, source = load_rotated_marker(family, variant)
            prepared[(family, variant)] = (mask, source)
            measured.append(thickness(mask))
            family_densities.setdefault(family, []).append(ink_density(mask))
    target = float(np.median(measured))
    corridor = (max(8.0, target - 3.0), target + 3.0)

    records = []
    paths = []
    for family, variants in MARKER_SELECTIONS.items():
        outputs = []
        density_median = float(np.median(family_densities[family]))
        for order, variant in enumerate(variants, 1):
            mask, source = prepared[(family, variant)]
            harmonized, audit = harmonize_stroke(mask, corridor, density_median)
            svg = marker_svg_source(harmonized, family)
            target_path = MARK_OUTPUT / family / f"{family}_{variant}.svg"
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(svg, encoding="utf-8")
            paths.append(target_path)
            outputs.append({
                "order": order,
                "variant": variant,
                "source": source.relative_to(WORK).as_posix(),
                "source_sha256": digest(source),
                "asset": target_path.relative_to(WORK / "04_harmony").as_posix(),
                "asset_sha256": digest(target_path),
                "rotation_degrees": MARKER_ROTATION_DEGREES,
                "rotation_direction": "counterclockwise",
                "canvas": list(MARKER_CANVAS),
                "stroke_audit": audit,
            })
        records.append({"family": family, "selected_variants": list(variants), "variants": outputs})

    selected = set(paths)
    if MARK_OUTPUT.is_dir():
        for stale in MARK_OUTPUT.glob("*/*.svg"):
            if stale not in selected:
                stale.unlink()
    audit = {
        "rotation_degrees": MARKER_ROTATION_DEGREES,
        "rotation_direction": "counterclockwise",
        "rotation_applied_before_harmonization": True,
        "all_markers_same_rotation": True,
        "source_assets_unchanged": True,
        "aspect_ratio_preserved": True,
        "stroke_strategy": "bounded topology-preserving shared marker corridor",
        "target_thickness": round(target, 3),
        "stroke_corridor": [round(value, 3) for value in corridor],
        "safe_margin": MARKER_SAFE_MARGIN,
        "canvas": list(MARKER_CANVAS),
    }
    return records, paths, audit


def inventory_digest(paths: list[Path]) -> str:
    payload = "".join(
        f"{path.relative_to(WORK).as_posix()}\0{digest(path)}\n" for path in sorted(paths)
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build() -> dict:
    if len(CHARACTER_ORDER) != 82 or set(SELECTIONS) != set(CHARACTER_ORDER):
        raise RuntimeError("Harmony selection must cover exactly the 82 target characters")
    if any(len(set(variants)) != 3 for variants in SELECTIONS.values()):
        raise RuntimeError("Every Harmony character needs exactly three distinct variants")

    prepared = {}
    class_measurements: dict[str, list[float]] = {}
    character_densities: dict[str, list[float]] = {}
    for character in CHARACTER_ORDER:
        for variant in SELECTIONS[character]:
            mask, path = load_normalized(character, variant)
            prepared[(character, variant)] = (mask, path)
            class_measurements.setdefault(stroke_class(character), []).append(thickness(mask))
            character_densities.setdefault(character, []).append(ink_density(mask))
    measured_class_targets = {
        key: float(np.median(values)) for key, values in class_measurements.items()
    }
    if set(measured_class_targets) != set(LOCKED_CLASS_TARGETS):
        raise RuntimeError("Locked Harmony stroke classes no longer match the master")
    class_targets = dict(LOCKED_CLASS_TARGETS)

    records = []
    output_paths = []
    for character in CHARACTER_ORDER:
        key = archive_name(character)
        density_median = LOCKED_CHARACTER_DENSITY_MEDIANS.get(
            character,
            float(np.median(character_densities[character])),
        )
        alternates = []
        for alternate, variant in enumerate(SELECTIONS[character], 1):
            mask, source = prepared[(character, variant)]
            harmonized, audit = harmonize_stroke(
                mask, target_corridor(character, class_targets), density_median
            )
            svg, advance = svg_source(harmonized, character)
            filename = f"{key}_{variant}.svg"
            target = OUTPUT / key / filename
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(svg, encoding="utf-8")
            output_paths.append(target)
            alternates.append({
                "alternate": alternate,
                "variant": variant,
                "source": source.relative_to(WORK).as_posix(),
                "source_sha256": digest(source),
                "asset": target.relative_to(WORK / "04_harmony").as_posix(),
                "asset_sha256": digest(target),
                "advance": advance,
                "canvas_height": CANVAS_HEIGHT,
                "visible_height": visible_geometry(character)[0],
                "stroke_audit": audit,
            })
        records.append({"character": character, "glyph_key": key, "alternates": alternates})

    selected_outputs = set(output_paths)
    for stale in OUTPUT.glob("*/*.svg"):
        if stale not in selected_outputs:
            stale.unlink()
    for directory in OUTPUT.iterdir():
        if directory.is_dir() and not any(directory.iterdir()):
            directory.rmdir()

    marker_records, marker_paths, marker_audit = build_markers()

    manifest = {
        "version": "CEOKlaue Final Master Harmony v1",
        "status": "final 82x3 master; SVG preview remains development/testing only",
        "character_order": CHARACTER_ORDER,
        "character_rows": list(CHARACTER_ROWS),
        "selected_characters": 82,
        "selected_glyphs": 246,
        "selection_order_defines_alternates": True,
        "mixing": {
            "seed": "sammlr-ceoklaue-final-master-v1",
            "method": "BLAKE2s(character, position, string seed), modulo three",
            "periodic_sequence": False,
        },
        "normalization": {
            "canvas_height": CANVAS_HEIGHT,
            "side_bearing": SIDE_BEARING,
            "aspect_ratio_preserved": True,
            "rotation": False,
            "baseline_jitter": False,
            "size_jitter": False,
            "blur": False,
            "stroke_strategy": "adaptive normalized thickness and ink-density corridor",
            "class_target_thickness": {
                key: round(value, 3) for key, value in class_targets.items()
            },
            "maximum_topology_preserving_morphology_steps": MAX_MORPHOLOGY_STEPS,
        },
        "characters": records,
        "asset_inventory_sha256": inventory_digest(output_paths),
        "selection_markers": {
            "status": "final separate handwritten assets; not font glyphs",
            "families": marker_records,
            "normalization": marker_audit,
            "selected_markers": 10,
            "asset_inventory_sha256": inventory_digest(marker_paths),
        },
        "product_assets_written": [],
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"Built {len(output_paths)} private Harmony glyph SVGs and "
        f"{len(marker_paths)} rotated marker SVGs: {manifest['asset_inventory_sha256']}"
    )
    return manifest


if __name__ == "__main__":
    build()
