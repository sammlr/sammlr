#!/usr/bin/env python3
"""Build the three bundled production fonts from the final 82x3 master."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parents[3]
WORK = ROOT / "Branding" / "CEOKlaue"
HARMONY = WORK / "04_harmony"
MANIFEST = WORK / "05_runtime" / "manifest.json"
RUNTIME = ROOT / "App" / "static" / "fonts"
MARKER_RUNTIME = ROOT / "App" / "static" / "ceoklaue-markers"
WORDMARK_RUNTIME = ROOT / "App" / "static" / "ceoklaue-wordmark.svg"
WORDMARK_SOURCE = WORK / "00_raw" / "ceoklaue_product_wordmark_final_01.jpg"
RUNTIME_NAMES = tuple(f"ceoklaue-final-alt{index}.woff2" for index in (1, 2, 3))
BASELINE_Y = 770
MIXING_SEED = "sammlr-ceoklaue-stickerlist-v1"
MARKER_MIXING_SEED = "sammlr-ceoklaue-stickerlist-markers-v1"
BODY_STROKE_FACTOR = 1.20
WORDMARK_STROKE_FACTOR = 1.65
MARKER_STROKE_FACTORS = {"receive_circle": 1.70, "give_cross": 1.70}
WORDMARK_COMPOSITION = (("s", 2), ("a", 1), ("m", 3), ("m", 2), ("l", 3), ("r", 3), (".", 2))
SAMMLR_PURPLE = "#7C3AED"

sys.path.insert(0, str(WORK / "03_font"))
sys.path.insert(0, str(HARMONY))

from build_ceoklaue import contours, safe_name, signed_area  # noqa: E402
import build_harmony_assets as harmony  # noqa: E402


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def strengthen_topology_preserving(mask: np.ndarray, factor: float) -> tuple[np.ndarray, dict]:
    """Increase optical stroke weight without closing counters or joining components."""
    original_topology = harmony.topology(mask)
    before = harmony.thickness(mask)
    target = before * factor
    result = mask.copy()
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    steps = 0
    while harmony.thickness(result) < target and steps < harmony.MAX_MORPHOLOGY_STEPS:
        candidate = cv2.dilate(result, kernel, iterations=1)
        if harmony.topology(candidate) != original_topology:
            break
        result = candidate
        steps += 1
    return result, {
        "strategy": "bounded topology-preserving dilation",
        "target_factor": factor,
        "thickness_before": round(before, 3),
        "thickness_after": round(harmony.thickness(result), 3),
        "steps": steps,
        "topology_before": list(original_topology),
        "topology_after": list(harmony.topology(result)),
    }


def svg_from_layers(layers: list[tuple[np.ndarray, str, str]], attributes: str = "") -> str:
    combined = np.maximum.reduce([mask for mask, _fill, _part in layers])
    points = cv2.findNonZero(combined)
    if points is None:
        raise RuntimeError("Cannot build an empty CEOKlaue runtime SVG")
    x, y, width, height = cv2.boundingRect(points)
    margin = 28
    top, bottom = max(0, y - margin), min(combined.shape[0], y + height + margin)
    left, right = max(0, x - margin), min(combined.shape[1], x + width + margin)
    paths = []
    for mask, fill, part in layers:
        cropped = mask[top:bottom, left:right]
        contours_found, _hierarchy = cv2.findContours(
            cropped, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE
        )
        commands = []
        for contour in contours_found:
            contour_points = contour[:, 0, :]
            if len(contour_points) < 3:
                continue
            commands.append(f"M {int(contour_points[0][0])} {int(contour_points[0][1])}")
            commands.extend(f"L {int(px)} {int(py)}" for px, py in contour_points[1:])
            commands.append("Z")
        paths.append(
            f'<path data-wordmark-part="{part}" d="{" ".join(commands)}" '
            f'fill="{fill}" fill-rule="evenodd"/>'
        )
    height, width = bottom - top, right - left
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {width} {height}" width="{width}" height="{height}" {attributes}>'
        f'{"".join(paths)}</svg>\n'
    )


def prepared_master():
    prepared = {}
    class_measurements: dict[str, list[float]] = {}
    character_densities: dict[str, list[float]] = {}
    for character in harmony.CHARACTER_ORDER:
        for variant in harmony.SELECTIONS[character]:
            mask, source = harmony.load_normalized(character, variant)
            prepared[(character, variant)] = (mask, source)
            class_measurements.setdefault(harmony.stroke_class(character), []).append(
                harmony.thickness(mask)
            )
            character_densities.setdefault(character, []).append(harmony.ink_density(mask))
    measured_class_targets = {
        key: float(np.median(values)) for key, values in class_measurements.items()
    }
    if set(measured_class_targets) != set(harmony.LOCKED_CLASS_TARGETS):
        raise RuntimeError("Locked runtime stroke classes no longer match the master")
    class_targets = dict(harmony.LOCKED_CLASS_TARGETS)
    return prepared, class_targets, character_densities


def font_glyph(character: str, mask: np.ndarray):
    pen = TTGlyphPen(None)
    top = harmony.visible_geometry(character)[1]
    for outline, depth in contours(mask):
        points = [
            (
                float(x) + harmony.SIDE_BEARING,
                float(BASELINE_Y - (float(y) + top)),
            )
            for x, y in outline
        ]
        want_clockwise = depth % 2 == 0
        is_clockwise = signed_area(points) < 0
        if is_clockwise != want_clockwise:
            points.reverse()
        pen.moveTo(points[0])
        for point in points[1:]:
            pen.lineTo(point)
        pen.closePath()
    advance = max(160, mask.shape[1] + 2 * harmony.SIDE_BEARING)
    return pen.glyph(), advance


def build_font(alternate: int, prepared, class_targets, character_densities) -> tuple[Path, list[dict]]:
    characters = list(harmony.CHARACTER_ORDER)
    glyph_order = [".notdef", "space"] + [safe_name(character) for character in characters]
    glyphs = {}
    metrics = {}
    stroke_audits = []

    notdef = TTGlyphPen(None)
    notdef.moveTo((80, 0))
    notdef.lineTo((80, 680))
    notdef.lineTo((520, 680))
    notdef.lineTo((520, 0))
    notdef.closePath()
    glyphs[".notdef"] = notdef.glyph()
    metrics[".notdef"] = (600, 0)
    glyphs["space"] = TTGlyphPen(None).glyph()
    metrics["space"] = (280, 0)

    for character in characters:
        variant = harmony.SELECTIONS[character][alternate - 1]
        mask, _source = prepared[(character, variant)]
        density_median = harmony.LOCKED_CHARACTER_DENSITY_MEDIANS.get(
            character,
            float(np.median(character_densities[character])),
        )
        harmonized, _audit = harmony.harmonize_stroke(
            mask,
            harmony.target_corridor(character, class_targets),
            density_median,
        )
        strengthened, strength_audit = strengthen_topology_preserving(
            harmonized, BODY_STROKE_FACTOR
        )
        stroke_audits.append({"character": character, **strength_audit})
        glyph, advance = font_glyph(character, strengthened)
        glyphs[safe_name(character)] = glyph
        metrics[safe_name(character)] = (advance, 0)

    family = f"CEOKlaue Final Alt {alternate}"
    builder = FontBuilder(1000, isTTF=True)
    builder.setupGlyphOrder(glyph_order)
    builder.setupCharacterMap(
        {ord(" "): "space", **{ord(character): safe_name(character) for character in characters}}
    )
    builder.setupGlyf(glyphs)
    builder.setupHorizontalMetrics(metrics)
    builder.setupHorizontalHeader(ascent=820, descent=-230, lineGap=0)
    builder.setupOS2(
        sTypoAscender=820,
        sTypoDescender=-230,
        sTypoLineGap=0,
        usWinAscent=850,
        usWinDescent=250,
        sxHeight=430,
        sCapHeight=620,
        usWeightClass=400,
        usWidthClass=5,
    )
    builder.setupNameTable(
        {
            "familyName": family,
            "styleName": "Regular",
            "uniqueFontIdentifier": f"Sammlr CEOKlaue Final Alt {alternate} v1",
            "fullName": f"{family} Regular",
            "psName": f"CEOKlaue-Final-Alt{alternate}",
            "version": "Version 1.0",
        }
    )
    builder.setupPost(italicAngle=0, underlinePosition=-110, underlineThickness=45)
    builder.setupMaxp()
    builder.font["head"].created = 2082844800
    builder.font["head"].modified = 2082844800
    builder.font.recalcTimestamp = False
    builder.font.flavor = "woff2"
    target = RUNTIME / RUNTIME_NAMES[alternate - 1]
    target.parent.mkdir(parents=True, exist_ok=True)
    builder.save(target)
    return target, stroke_audits


def build_wordmark(_prepared, _class_targets, _character_densities) -> tuple[Path, dict]:
    """Vectorize the PO's connected one-image wordmark without recomposition."""
    if not WORDMARK_SOURCE.is_file():
        raise RuntimeError(f"Missing final individual wordmark source: {WORDMARK_SOURCE}")
    photo = np.asarray(ImageOps.exif_transpose(Image.open(WORDMARK_SOURCE)).convert("RGB"))
    crop = photo[1300:2050, 100:2900]
    gray = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY)
    raw = np.where(gray < 75, 255, 0).astype(np.uint8)
    count, labels, stats, centers = cv2.connectedComponentsWithStats(raw, 8)
    kept = [index for index in range(1, count) if int(stats[index, cv2.CC_STAT_AREA]) >= 1000]
    if len(kept) != 7:
        raise RuntimeError(f"Final wordmark must resolve to six letters and one period, got {len(kept)}")
    period_component = max(kept, key=lambda index: float(centers[index][0]))
    letters_canvas = np.where(
        np.isin(labels, [index for index in kept if index != period_component]), 255, 0
    ).astype(np.uint8)
    period_canvas = np.where(labels == period_component, 255, 0).astype(np.uint8)
    attributes = (
        'data-text="sammlr." data-source-mode="single-connected-image" '
        f'data-letter-color="#211d22" data-period-color="{SAMMLR_PURPLE}"'
    )
    WORDMARK_RUNTIME.write_text(
        svg_from_layers(
            [
                (letters_canvas, "#211d22", "letters"),
                (period_canvas, SAMMLR_PURPLE, "period"),
            ],
            attributes,
        ),
        encoding="utf-8",
    )
    return WORDMARK_RUNTIME, {
        "status": "final productive wordmark from the PO's individual connected source image",
        "text": "sammlr.",
        "source_mode": "single-connected-image",
        "source": WORDMARK_SOURCE.relative_to(ROOT).as_posix(),
        "source_sha256": digest(WORDMARK_SOURCE),
        "letter_color": "#211d22",
        "period_color": SAMMLR_PURPLE,
        "stroke_strategy": "faithful threshold vectorization; no letter recomposition",
        "asset": WORDMARK_RUNTIME.relative_to(ROOT).as_posix(),
        "asset_sha256": digest(WORDMARK_RUNTIME),
        "connected_wordmark_preserved": True,
    }


def build_runtime_markers(harmony_markers: dict) -> tuple[list[Path], list[dict]]:
    prepared = {}
    measurements = []
    family_densities: dict[str, list[float]] = {}
    for family in harmony_markers["families"]:
        family_name = family["family"]
        for variant in family["variants"]:
            mask, _source = harmony.load_rotated_marker(family_name, variant["variant"])
            prepared[(family_name, variant["variant"])] = mask
            measurements.append(harmony.thickness(mask))
            family_densities.setdefault(family_name, []).append(harmony.ink_density(mask))
    shared_target = float(np.median(measurements))
    corridor = (max(8.0, shared_target - 3.0), shared_target + 3.0)

    marker_paths = []
    marker_records = []
    for family in harmony_markers["families"]:
        family_name = family["family"]
        runtime_variants = []
        for variant in family["variants"]:
            if variant.get("rotation_degrees") != -90:
                raise RuntimeError("Marker rotation audit escaped the binding -90 degree rule")
            mask = prepared[(family_name, variant["variant"])]
            harmonized, _audit = harmony.harmonize_stroke(
                mask, corridor, float(np.median(family_densities[family_name]))
            )
            strengthened, strength_audit = strengthen_topology_preserving(
                harmonized, MARKER_STROKE_FACTORS[family_name]
            )
            fill = SAMMLR_PURPLE if family_name == "receive_circle" else "#211d22"
            svg = harmony.marker_svg_source(strengthened, family_name)
            svg = svg.replace('fill="#211d22"', f'fill="{fill}"')
            svg = svg.replace(
                f'data-marker-family="{family_name}"',
                f'data-marker-family="{family_name}" data-runtime-color="{fill}" '
                f'data-runtime-stroke-factor="{MARKER_STROKE_FACTORS[family_name]}"',
            )
            target = MARKER_RUNTIME / family_name / Path(variant["asset"]).name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(svg, encoding="utf-8")
            marker_paths.append(target)
            runtime_variants.append({
                "order": variant["order"],
                "variant": variant["variant"],
                "source": variant["source"],
                "source_sha256": variant["source_sha256"],
                "harmony_asset": variant["asset"],
                "harmony_asset_sha256": variant["asset_sha256"],
                "runtime_asset": target.relative_to(ROOT).as_posix(),
                "runtime_asset_sha256": digest(target),
                "rotation_degrees": -90,
                "rotation_direction": "counterclockwise",
                "color": fill,
                "stroke_audit": strength_audit,
            })
        marker_records.append({
            "family": family_name,
            "selected_variants": family["selected_variants"],
            "runtime_color": SAMMLR_PURPLE if family_name == "receive_circle" else "#211d22",
            "stroke_factor": MARKER_STROKE_FACTORS[family_name],
            "variants": runtime_variants,
        })
    return marker_paths, marker_records


def build() -> dict:
    harmony_manifest = json.loads((HARMONY / "manifest.json").read_text(encoding="utf-8"))
    if harmony_manifest.get("version") != "CEOKlaue Final Master Harmony v1":
        raise RuntimeError("Final Harmony master must be built before the runtime fonts")
    expected = {
        record["character"]: tuple(
            alternate["variant"] for alternate in record["alternates"]
        )
        for record in harmony_manifest["characters"]
    }
    if expected != harmony.SELECTIONS:
        raise RuntimeError("Harmony manifest and binding final selections disagree")
    harmony_markers = harmony_manifest.get("selection_markers", {})
    if harmony_markers.get("selected_markers") != 10:
        raise RuntimeError("Final Harmony master must contain ten selection markers")
    if harmony_markers.get("normalization", {}).get("rotation_degrees") != -90:
        raise RuntimeError("Every final marker must be rotated exactly 90 degrees left")

    prepared, class_targets, character_densities = prepared_master()
    font_results = [
        build_font(alternate, prepared, class_targets, character_densities)
        for alternate in (1, 2, 3)
    ]
    runtime_paths = [result[0] for result in font_results]
    font_stroke_audits = [result[1] for result in font_results]
    wordmark_path, wordmark_record = build_wordmark(
        prepared, class_targets, character_densities
    )
    legacy_runtime = RUNTIME / "ceoklaue-v0.1.woff2"
    if legacy_runtime.exists():
        legacy_runtime.unlink()

    marker_paths, marker_records = build_runtime_markers(harmony_markers)
    selected_marker_paths = set(marker_paths)
    if MARKER_RUNTIME.is_dir():
        for stale in MARKER_RUNTIME.glob("*/*.svg"):
            if stale not in selected_marker_paths:
                stale.unlink()

    master_records = []
    for record in harmony_manifest["characters"]:
        master_records.append(
            {
                "character": record["character"],
                "glyph_key": record["glyph_key"],
                "alternates": [
                    {
                        "alternate": alternate["alternate"],
                        "variant": alternate["variant"],
                        "source": alternate["source"],
                        "source_sha256": alternate["source_sha256"],
                        "harmony_asset": alternate["asset"],
                        "harmony_asset_sha256": alternate["asset_sha256"],
                    }
                    for alternate in record["alternates"]
                ],
            }
        )

    inventory_payload = "".join(
        f"{path.relative_to(ROOT).as_posix()}\0{digest(path)}\n" for path in runtime_paths
    )
    manifest = {
        "version": "CEOKlaue Final Production Runtime v1",
        "master": {
            "characters": 82,
            "selected_glyphs": 246,
            "selection_order_defines_alternates": True,
            "harmony_manifest": "04_harmony/manifest.json",
            "harmony_manifest_sha256": digest(HARMONY / "manifest.json"),
            "characters_manifest": master_records,
        },
        "runtime": {
            "strategy": "three bundled local WOFF2 fonts; one complete selected alternate per font",
            "public_assets": [path.relative_to(ROOT).as_posix() for path in runtime_paths],
            "assets": [
                {
                    "alternate": index,
                    "path": path.relative_to(ROOT).as_posix(),
                    "sha256": digest(path),
                }
                for index, path in enumerate(runtime_paths, 1)
            ],
            "asset_inventory_sha256": hashlib.sha256(
                inventory_payload.encode("utf-8")
            ).hexdigest(),
            "external_assets": [],
            "body_stroke_adjustment": {
                "factor": BODY_STROKE_FACTOR,
                "strategy": "bounded topology-preserving dilation after accepted Harmony",
                "browser_synthetic_bold": False,
                "audits": font_stroke_audits,
            },
        },
        "mixing": {
            "seed": MIXING_SEED,
            "method": "FNV-1a 32-bit over seed, full string, character, position and stable context; modulo three with deterministic previous-occurrence anti-repetition",
            "runtime_randomness": False,
            "reload_stable": True,
            "simple_periodic_sequence": False,
            "repeated_character_anti_repetition": True,
        },
        "scope": ["sticker-list-page"],
        "header_wordmark": wordmark_record,
        "selection_markers": {
            "status": "final productive handwritten assets; separate from font glyphs",
            "families": marker_records,
            "selected_markers": 10,
            "rotation_degrees": -90,
            "rotation_direction": "counterclockwise",
            "source_assets_unchanged": True,
            "mixing": {
                "seed": MARKER_MIXING_SEED,
                "method": "FNV-1a 32-bit over seed, family, code, instance and stable album context; modulo five",
                "runtime_randomness": False,
                "reload_stable": True,
                "simple_periodic_sequence": False,
            },
            "public_assets": [path.relative_to(ROOT).as_posix() for path in marker_paths],
            "asset_inventory_sha256": hashlib.sha256(
                "".join(
                    f"{path.relative_to(ROOT).as_posix()}\0{digest(path)}\n"
                    for path in marker_paths
                ).encode("utf-8")
            ).hexdigest(),
        },
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        "Built three final bundled CEOKlaue runtime fonts: "
        f"{manifest['runtime']['asset_inventory_sha256']}"
    )
    return manifest


if __name__ == "__main__":
    build()
