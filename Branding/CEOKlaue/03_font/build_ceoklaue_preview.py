#!/usr/bin/env python3
"""Build the local-only CEOKlaue v0.2 preview font from archived glyphs.

This builder never writes into App/static.  It consumes the already extracted
v0.1 PNG masks, applies one moderate contour expansion and writes explicitly
non-final preview assets below 03_font/preview.
"""

from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont
from PIL import Image

from build_ceoklaue import (
    DESCENDERS,
    LOWERCASE,
    PUNCTUATION,
    archive_name,
    contours,
    safe_name,
    signed_area,
)


ROOT = Path(__file__).resolve().parents[3]
EXTRACTED = ROOT / "Branding" / "CEOKlaue" / "01_extracted" / "glyphs"
OUTPUT = Path(__file__).resolve().parent / "preview"

CHAR_ORDER = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789äöüß.,:!?-+/()"
OPEN_SELECTIONS = {"K": "03", "P": "03", "k": "03", "0": "03"}
PO_SELECTIONS = {
    "A": "03", "B": "05", "C": "01", "D": "04", "E": "03", "F": "03",
    "G": "01", "H": "01", "I": "01", "J": "04", "L": "04", "M": "03",
    "N": "03", "O": "05", "Q": "04", "R": "02", "S": "05", "T": "02",
    "U": "04", "V": "03", "W": "02", "X": "05", "Y": "03", "Z": "01",
    "a": "03", "b": "05", "c": "04", "d": "02", "e": "03", "f": "05",
    "g": "03", "h": "05", "i": "04", "j": "05", "l": "03", "m": "02",
    "n": "05", "o": "04", "p": "02", "q": "05", "r": "03", "s": "03",
    "t": "04", "u": "05", "v": "02", "w": "05", "x": "05", "y": "02",
    "z": "02", "1": "01", "2": "03", "3": "01", "4": "02", "5": "02",
    "6": "01", "7": "05", "8": "03", "9": "05", "ä": "04", "ö": "05",
    "ü": "04", "ß": "05", ".": "03", ",": "03", ":": "05", "!": "05",
    "?": "01", "-": "04", "+": "02", "/": "03", "(": "04", ")": "04",
}
SELECTIONS = {**PO_SELECTIONS, **OPEN_SELECTIONS}
CRITICAL_COUNTERS = "ea68BR"
THICKENING_KERNEL = (3, 3)
THICKENING_ITERATIONS = 1

# Optical normalization uses restrained, uniform per-glyph scaling. Characters
# already inside their group's visual corridor remain at 1.0 so the handwriting
# does not become mechanically even. K/P/k/0 deliberately keep variant 03;
# normalization never changes the selected source.
NORMALIZATION_FACTORS = {
    # Capitals: approximate visible-height corridor 460–520 font units.
    "B": 1.06, "C": 1.11, "D": 1.23, "E": 1.08, "F": 1.16,
    "H": 0.96, "I": 1.06, "L": 1.08, "N": 0.93, "O": 1.14, "P": 1.10,
    "Q": 1.11, "T": 1.16, "U": 1.30, "V": 0.95, "X": 0.96,
    "Z": 1.08,
    # Lowercase: preserve ascenders/descenders, normalize the body family.
    "a": 0.85, "d": 0.95, "e": 1.11, "f": 0.86, "h": 0.93,
    "p": 1.18, "u": 1.10, "x": 0.95, "y": 1.13, "ß": 0.82,
    # Digits: approximate visible-height corridor 470–535 font units.
    "2": 0.93, "3": 0.95, "4": 1.07, "6": 0.91,
    # Umlauts are scaled as whole handwritten glyphs, including their dots.
    "ä": 1.05, "ö": 1.18, "ü": 1.15,
}
CAP_HEIGHT = 500
X_HEIGHT = 390
SIDE_BEARING = 45
DETERMINISTIC_FONT_TIMESTAMP = 2082844800  # 1970-01-01 in the OpenType epoch.


def source_path(char: str, variant: str) -> Path:
    name = archive_name(char)
    return EXTRACTED / name / f"{name}_{variant}.png"


def load_mask(char: str, variant: str) -> np.ndarray:
    path = source_path(char, variant)
    if not path.is_file():
        raise RuntimeError(f"Missing archived preview source: {path}")
    return np.asarray(Image.open(path).convert("RGBA"))[:, :, 3]


def hole_count(mask: np.ndarray) -> int:
    _found, hierarchy = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    if hierarchy is None:
        return 0
    return sum(1 for node in hierarchy[0] if node[3] != -1)


def thicken(mask: np.ndarray) -> np.ndarray:
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, THICKENING_KERNEL)
    return cv2.dilate(mask, kernel, iterations=THICKENING_ITERATIONS)


def preview_glyph(char: str, mask: np.ndarray):
    if char in LOWERCASE:
        scale = 11.2
    elif char.isdigit():
        scale = 10.8
    elif char in PUNCTUATION:
        scale = 10.0
    else:
        scale = 10.4

    if char in DESCENDERS:
        y_offset = -185
    elif char == ",":
        y_offset = -105
    elif char in ".-":
        y_offset = 35 if char == "." else 250
    elif char == ":":
        y_offset = 175
    elif char == "+":
        y_offset = 125
    elif char in "()":
        y_offset = -55
    else:
        y_offset = 0

    factor = NORMALIZATION_FACTORS.get(char, 1.0)
    outlines = contours(mask)
    if not outlines:
        raise RuntimeError(f"No contours available for {char}")
    all_points = [point for outline, _depth in outlines for point in outline]
    min_x = min(float(point[0]) for point in all_points)
    max_x = max(float(point[0]) for point in all_points)
    max_y = max(float(point[1]) for point in all_points)

    pen = TTGlyphPen(None)
    for outline, depth in outlines:
        points = [
            (
                (float(x) - min_x) * scale * factor + SIDE_BEARING,
                (max_y - float(y)) * scale * factor + y_offset,
            )
            for x, y in outline
        ]
        want_clockwise = depth % 2 == 0
        if (signed_area(points) < 0) != want_clockwise:
            points.reverse()
        pen.moveTo(points[0])
        for point in points[1:]:
            pen.lineTo(point)
        pen.closePath()

    advance = max(220, round((max_x - min_x) * scale * factor + 2 * SIDE_BEARING))
    if char in "il.,:!":
        advance = max(170, advance - 20)
    return pen.glyph(), advance


def build_preview_font() -> dict:
    if set(SELECTIONS) != set(CHAR_ORDER):
        missing = sorted(set(CHAR_ORDER) - set(SELECTIONS))
        extra = sorted(set(SELECTIONS) - set(CHAR_ORDER))
        raise RuntimeError(f"Preview selection mismatch; missing={missing}, extra={extra}")

    glyph_order = [".notdef", "space"] + [safe_name(char) for char in CHAR_ORDER]
    built = {}
    metrics = {}
    counter_audit = {}

    notdef = TTGlyphPen(None)
    notdef.moveTo((80, 0)); notdef.lineTo((80, 680)); notdef.lineTo((520, 680))
    notdef.lineTo((520, 0)); notdef.closePath()
    built[".notdef"] = notdef.glyph()
    metrics[".notdef"] = (600, 0)
    built["space"] = TTGlyphPen(None).glyph()
    metrics["space"] = (280, 0)

    for char in CHAR_ORDER:
        original = load_mask(char, SELECTIONS[char])
        thickened = thicken(original)
        if char in CRITICAL_COUNTERS:
            before = hole_count(original)
            after = hole_count(thickened)
            counter_audit[char] = {"before": before, "after": after}
            if after < before:
                raise RuntimeError(f"Contour expansion closes an interior space in {char}")
        glyph, advance = preview_glyph(char, thickened)
        name = safe_name(char)
        built[name] = glyph
        metrics[name] = (advance, SIDE_BEARING)

    builder = FontBuilder(1000, isTTF=True)
    builder.setupGlyphOrder(glyph_order)
    builder.setupCharacterMap({ord(" "): "space", **{ord(c): safe_name(c) for c in CHAR_ORDER}})
    builder.setupGlyf(built)
    builder.setupHorizontalMetrics(metrics)
    builder.setupHorizontalHeader(ascent=960, descent=-230, lineGap=30)
    builder.setupOS2(
        sTypoAscender=820, sTypoDescender=-230, sTypoLineGap=50,
        usWinAscent=980, usWinDescent=250, sxHeight=X_HEIGHT, sCapHeight=CAP_HEIGHT,
        usWeightClass=450, usWidthClass=5,
    )
    builder.setupNameTable({
        "familyName": "CEOKlaue v0.2 Preview",
        "styleName": "Regular",
        "uniqueFontIdentifier": "Sammlr CEOKlaue v0.2 Preview - not final",
        "fullName": "CEOKlaue v0.2 Preview Regular",
        "psName": "CEOKlaue-v0.2-Preview",
        "version": "Version 0.2 Preview",
    })
    builder.setupPost(italicAngle=0, underlinePosition=-110, underlineThickness=45)
    builder.setupMaxp()
    builder.font.recalcTimestamp = False
    builder.font["head"].created = DETERMINISTIC_FONT_TIMESTAMP
    builder.font["head"].modified = DETERMINISTIC_FONT_TIMESTAMP

    OUTPUT.mkdir(parents=True, exist_ok=True)
    ttf_path = OUTPUT / "CEOKlaue-v0.2-preview.ttf"
    woff2_path = OUTPUT / "CEOKlaue-v0.2-preview.woff2"
    builder.save(ttf_path)
    woff = TTFont(ttf_path, recalcTimestamp=False)
    woff.flavor = "woff2"
    woff.save(woff2_path)

    manifest = {
        "version": "CEOKlaue v0.2 Preview (not final)",
        "source": "Branding/CEOKlaue/01_extracted/glyphs",
        "character_order": CHAR_ORDER,
        "po_selections": PO_SELECTIONS,
        "open_selections_using_v0.1_variant_03": OPEN_SELECTIONS,
        "missing_source_backed_characters": "ÄÖÜ;",
        "contour_thickening": {
            "method": "binary mask dilation before vectorization",
            "kernel": list(THICKENING_KERNEL),
            "kernel_shape": "ellipse",
            "iterations": THICKENING_ITERATIONS,
        },
        "critical_counter_audit": counter_audit,
        "normalization": {
            "strategy": "uniform optical outlier scaling with preserved group variation",
            "factors": NORMALIZATION_FACTORS,
            "unchanged_factor": 1.0,
            "side_bearing_units": SIDE_BEARING,
            "cap_height_units": CAP_HEIGHT,
            "x_height_units": X_HEIGHT,
            "hhea": {"ascent": 960, "descent": -230, "line_gap": 30},
            "os2_typographic": {"ascent": 820, "descent": -230, "line_gap": 50},
            "os2_windows": {"ascent": 980, "descent": 250},
            "vertical_anchor": "ink bottom aligned by glyph class; descenders retain -185",
        },
        "public_runtime_assets": [],
    }
    (OUTPUT / "build-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


if __name__ == "__main__":
    result = build_preview_font()
    print(
        "Built local-only CEOKlaue v0.2 preview with "
        f"{len(result['po_selections'])} PO selections and "
        f"{len(result['open_selections_using_v0.1_variant_03'])} open fallbacks"
    )
