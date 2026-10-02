#!/usr/bin/env python3
"""Build CEOKlaue v0.1 only from the photographs in ../00_raw.

This is a reproducible, local build tool.  It keeps the source photographs
private, archives five written variants where the sheet provides them and
publishes only the finished WOFF2 into App/static/fonts.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont


ROOT = Path(__file__).resolve().parents[3]
WORK = ROOT / "Branding" / "CEOKlaue"
RAW = WORK / "00_raw"
EXTRACTED = WORK / "01_extracted"
VECTORS = WORK / "02_vectors"
FONT = WORK / "03_font"
SIGNATURE = WORK / "04_signature"
RUNTIME = ROOT / "App" / "static" / "fonts"

SOURCES = {
    "upper": "ceoklaue_alphabet_upper_01.jpg",
    "lower": "ceoklaue_alphabet_lower_symbols_01.jpg",
    "numbers": "ceoklaue_numbers_words_01.jpg",
    "codes": "ceoklaue_codes_reference_01.jpg",
}

# Optional, separately imported completion sheets.  They are intentionally not
# consumed by the v0.1 builder, but are valid members of 00_raw after the final
# completion-source import.
OPTIONAL_COMPLETION_SOURCES = {
    "ceoklaue_completion_caps_lower_01.jpeg",
    "ceoklaue_completion_numbers_umlauts_01.jpeg",
    "ceoklaue_completion_symbols_01.jpeg",
    "ceoklaue_final_reselection_01.jpg",
    "ceoklaue_final_reselection_02.jpg",
}

UPPER_LEFT_ROWS = dict(zip("ABCDEFGHIJKLMNOPQ", [
    (138, 205), (210, 272), (282, 347), (356, 422), (430, 500),
    (505, 573), (580, 652), (654, 730), (727, 805), (800, 884),
    (882, 956), (955, 1031), (1027, 1115), (1108, 1188),
    (1187, 1268), (1260, 1340), (1340, 1430),
]))
UPPER_RIGHT_ROWS = dict(zip("RSTUVWXYZ", [
    (138, 205), (210, 272), (282, 347), (356, 422), (430, 500),
    (505, 573), (580, 652), (654, 730), (727, 805),
]))
UPPER_LEFT_COLS = [(195, 250), (250, 300), (300, 350), (350, 400), (400, 462)]
UPPER_LEFT_CENTERS = {
    "A": [234, 282, 326, 369, 416], "B": [235, 286, 336, 385, 433],
    "C": [232, 284, 330, 379, 426], "D": [234, 288, 336, 384, 428],
    "E": [230, 284, 332, 387, 428], "F": [230, 278, 326, 377, 418],
    "G": [221, 278, 330, 380, 422], "H": [228, 278, 328, 374, 415],
    "I": [225, 277, 329, 377, 421], "J": [226, 278, 330, 386, 433],
    "K": [228, 279, 331, 380, 435], "L": [226, 279, 330, 385, 435],
    "M": [230, 293, 362, 424, 475], "N": [230, 284, 346, 405, 446],
    "O": [224, 280, 338, 387, 441], "P": [228, 278, 332, 382, 432],
    "Q": [224, 277, 330, 383, 435],
}
UPPER_RIGHT_COLS = [(475, 530), (530, 578), (578, 625), (625, 675), (675, 735)]

LOWER_LEFT_ROWS = dict(zip("abcdefghijklmnopqrs", [
    (88, 158), (158, 228), (238, 303), (305, 385), (395, 460),
    (458, 538), (538, 620), (612, 690), (700, 765), (760, 835),
    (825, 920), (918, 990), (1008, 1072), (1064, 1126),
    (1128, 1200), (1198, 1272), (1270, 1345), (1340, 1414),
    (1405, 1475),
]))
LOWER_RIGHT_ROWS = {
    "t": (88, 158), "u": (155, 218), "v": (225, 282),
    "w": (276, 340), "x": (332, 390), "y": (388, 460),
    "z": (470, 525), "ä": (520, 590), "ö": (585, 645),
    "ü": (640, 696), "ß": (690, 770),
}
LOWER_LEFT_COLS = [(172, 228), (228, 280), (280, 332), (332, 386), (386, 452)]
LOWER_LEFT_CENTERS = {
    "a": [209, 255, 313, 371, 428], "b": [203, 257, 310, 359, 407],
    "c": [198, 235, 270, 317, 360], "d": [198, 241, 289, 340, 377],
    "e": [201, 244, 292, 337, 382], "f": [200, 240, 276, 311, 345],
    "g": [191, 240, 280, 325, 376], "h": [197, 252, 304, 352, 395],
    "i": [190, 241, 297, 347, 397], "j": [191, 244, 296, 343, 392],
    "k": [198, 246, 298, 351, 399], "l": [189, 242, 291, 345, 395],
    "m": [201, 281, 357, 433], "n": [198, 253, 317, 375, 428],
    "o": [198, 251, 315, 373, 428], "p": [197, 248, 305, 364, 415],
    "q": [195, 248, 299, 366, 414], "r": [199, 249, 298, 344, 389],
    "s": [200, 248, 303, 350, 385],
}
LOWER_RIGHT_COLS = [(478, 528), (528, 578), (578, 628), (628, 678), (678, 746)]
LOWER_RIGHT_CENTERS = {
    "t": [507, 543, 574, 610, 643], "u": [505, 558, 599, 637, 679],
    "v": [505, 555, 599, 649, 681], "w": [508, 590, 656, 720, 773],
    "x": [506, 552, 605, 652, 707], "y": [502, 554, 605, 657, 706],
    "z": [503, 554, 605, 668, 720], "ä": [500, 550, 595, 640, 685],
    "ö": [500, 545, 600, 640, 678], "ü": [500, 550, 595, 642, 679],
    "ß": [505, 554, 605, 647, 688],
}

NUMBER_ROWS = dict(zip("0123456789", [
    (55, 116), (120, 190), (190, 267), (265, 338), (337, 410),
    (412, 488), (488, 560), (560, 632), (632, 704), (704, 778),
]))
NUMBER_COLS = [(222, 282), (282, 334), (334, 389), (389, 444), (444, 510)]

SPECIALS = {
    ".": ((785, 815), [(480, 515), (515, 545), (545, 575), (575, 600), (600, 630)]),
    ",": ((815, 852), [(485, 518), (518, 546), (546, 575), (575, 596), (596, 622)]),
    ":": ((858, 900), [(480, 512), (512, 544), (544, 568), (568, 594), (594, 622)]),
    "!": ((895, 945), [(480, 515), (515, 545), (545, 570), (570, 595), (595, 622)]),
    "?": ((942, 1005), [(478, 515), (515, 548), (548, 580), (580, 608), (608, 638)]),
    "+": ((1015, 1075), [(470, 532), (532, 574), (574, 604), (604, 631), (631, 692)]),
    "-": ((1080, 1110), [(525, 566), (566, 604), (604, 640), (640, 674), (674, 712)]),
    "/": ((1118, 1172), [(478, 510), (510, 538), (538, 566), (566, 592), (592, 622)]),
    "&": ((1172, 1240), [(470, 512), (512, 552), (552, 589), (589, 629), (629, 680)]),
    "(": ((1240, 1300), [(468, 492), (492, 525), (525, 552), (552, 585), (585, 615)]),
    ")": ((1298, 1362), [(470, 505), (505, 536), (536, 566), (566, 595), (595, 620)]),
    "%": ((1365, 1432), [(468, 515), (515, 562), (562, 610), (610, 652), (652, 695)]),
}

CANONICAL_VARIANT = 3
DESCENDERS = set("gjpqy")
LOWERCASE = set("abcdefghijklmnopqrstuvwxyzäöüß")
PUNCTUATION = set(".,:!?-+/&%()")


def safe_name(char: str) -> str:
    names = {
        ".": "period", ",": "comma", ":": "colon", "!": "exclam",
        "?": "question", "-": "hyphen", "+": "plus", "/": "slash",
        "&": "ampersand", "%": "percent", "(": "parenleft",
        ")": "parenright", "ä": "adieresis", "ö": "odieresis",
        "ü": "udieresis", "ß": "germandbls", " ": "space",
    }
    return names.get(char, f"uni{ord(char):04X}" if not char.isascii() else char)


def archive_name(char: str) -> str:
    """Use case-independent paths so uppercase/lowercase never collide on macOS."""
    if "A" <= char <= "Z":
        return f"cap_{char}"
    if "a" <= char <= "z":
        return f"lower_{char}"
    return safe_name(char)


def clean_mask(gray: np.ndarray) -> np.ndarray:
    # The black ballpoint is consistently darker than the printed grey grid.
    # A conservative threshold retains small pressure variations without
    # admitting the paper texture or the grid into the glyph.
    mask = np.where(gray < 70, 255, 0).astype(np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((2, 2), np.uint8))
    count, labels, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    cleaned = np.zeros_like(mask)
    for index in range(1, count):
        x, y, width, height, area = stats[index]
        if area < 5:
            continue
        # Residual crop-spanning graph-paper lines are not handwriting.
        if width > mask.shape[1] * .88 and height <= 3:
            continue
        if height > mask.shape[0] * .88 and width <= 3:
            continue
        cleaned[labels == index] = 255
    return cleaned


def cropped_mask(image: np.ndarray, box: tuple[int, int, int, int]) -> np.ndarray:
    x0, y0, x1, y1 = box
    mask = clean_mask(image[y0:y1, x0:x1])
    count, labels, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    component_areas = [int(stats[index, cv2.CC_STAT_AREA]) for index in range(1, count)]
    if component_areas:
        relative_floor = max(5, int(max(component_areas) * .08))
        selected = np.zeros_like(mask)
        for index, area in enumerate(component_areas, 1):
            if area >= relative_floor:
                selected[labels == index] = 255
        mask = selected
    # One pixel of optical weight makes the photographed ballpoint survive at
    # the 20–24 px sizes used by the sticker list without smoothing its edges.
    mask = cv2.dilate(mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)), iterations=1)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    points = cv2.findNonZero(mask)
    if points is None:
        raise RuntimeError(f"No ink found in crop {box}")
    x, y, width, height = cv2.boundingRect(points)
    pad = 3
    return cv2.copyMakeBorder(
        mask[max(0, y - pad):min(mask.shape[0], y + height + pad),
             max(0, x - pad):min(mask.shape[1], x + width + pad)],
        pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=0,
    )


def save_png(mask: np.ndarray, path: Path) -> None:
    rgba = np.zeros((*mask.shape, 4), dtype=np.uint8)
    rgba[:, :, :3] = 20
    rgba[:, :, 3] = mask
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(rgba, "RGBA").save(path)


def contours(mask: np.ndarray):
    found, hierarchy = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    if hierarchy is None:
        return []
    hierarchy = hierarchy[0]
    result = []
    for index, contour in enumerate(found):
        if abs(cv2.contourArea(contour)) < 2:
            continue
        approximate = cv2.approxPolyDP(contour, .72, True).reshape(-1, 2)
        if len(approximate) < 3:
            continue
        depth = 0
        parent = hierarchy[index][3]
        while parent != -1:
            depth += 1
            parent = hierarchy[parent][3]
        result.append((approximate, depth))
    return result


def save_svg(mask: np.ndarray, path: Path) -> None:
    pieces = []
    for contour, _ in contours(mask):
        points = contour.tolist()
        pieces.append("M " + " L ".join(f"{x} {y}" for x, y in points) + " Z")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {mask.shape[1]} {mask.shape[0]}">'
        f'<path fill="#171419" fill-rule="nonzero" d="{" ".join(pieces)}"/></svg>\n',
        encoding="utf-8",
    )


def add_row_crops(target, image, source_name, rows, columns):
    for char, (y0, y1) in rows.items():
        target.setdefault(char, [])
        for variant, (x0, x1) in enumerate(columns, 1):
            mask = cropped_mask(image, (x0, y0, x1, y1))
            target[char].append((source_name, variant, mask))


def add_center_crops(target, image, source_name, rows, centers_by_char):
    for char, (y0, y1) in rows.items():
        target.setdefault(char, [])
        centers = centers_by_char[char]
        distances = [centers[index + 1] - centers[index] for index in range(len(centers) - 1)]
        for variant, center in enumerate(centers, 1):
            left_gap = distances[variant - 2] if variant > 1 else distances[0]
            right_gap = distances[variant - 1] if variant < len(centers) else distances[-1]
            x0 = int(center - left_gap * .46)
            x1 = int(center + right_gap * .46)
            mask = cropped_mask(image, (x0, y0, x1, y1))
            target[char].append((source_name, variant, mask))


def extract_all():
    images = {
        key: cv2.imread(str(RAW / filename), cv2.IMREAD_GRAYSCALE)
        for key, filename in SOURCES.items()
    }
    if any(image is None for image in images.values()):
        raise RuntimeError("One or more declared raw source photographs are unreadable")

    glyphs = {}
    add_center_crops(glyphs, images["upper"], SOURCES["upper"], UPPER_LEFT_ROWS, UPPER_LEFT_CENTERS)
    add_row_crops(glyphs, images["upper"], SOURCES["upper"], UPPER_RIGHT_ROWS, UPPER_RIGHT_COLS)
    add_center_crops(glyphs, images["lower"], SOURCES["lower"], LOWER_LEFT_ROWS, LOWER_LEFT_CENTERS)
    add_center_crops(glyphs, images["lower"], SOURCES["lower"], LOWER_RIGHT_ROWS, LOWER_RIGHT_CENTERS)
    add_row_crops(glyphs, images["numbers"], SOURCES["numbers"], NUMBER_ROWS, NUMBER_COLS)
    for char, ((y0, y1), columns) in SPECIALS.items():
        glyphs.setdefault(char, [])
        for variant, (x0, x1) in enumerate(columns, 1):
            mask = cropped_mask(images["lower"], (x0, y0, x1, y1))
            glyphs[char].append((SOURCES["lower"], variant, mask))

    for char, variants in glyphs.items():
        name = archive_name(char)
        for source_name, variant, mask in variants:
            stem = f"{name}_{variant:02d}"
            save_png(mask, EXTRACTED / "glyphs" / name / f"{stem}.png")
            save_svg(mask, VECTORS / "glyphs" / name / f"{stem}.svg")

    # The source photograph actually reads “Sammler.” (with an e).  Preserve it
    # exactly as source evidence, but do not ship it as the Sammlr. runtime mark.
    signature_mask = cropped_mask(images["numbers"], (218, 778, 535, 855))
    save_png(signature_mask, EXTRACTED / "signature" / "source_sammler_01.png")
    save_png(signature_mask, SIGNATURE / "ceoklaue_source_sammler.png")
    save_svg(signature_mask, SIGNATURE / "ceoklaue_source_sammler.svg")
    return glyphs


def signed_area(points):
    return sum(
        points[index][0] * points[(index + 1) % len(points)][1]
        - points[(index + 1) % len(points)][0] * points[index][1]
        for index in range(len(points))
    ) / 2


def glyph_from_mask(char: str, mask: np.ndarray):
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
    elif char in "+":
        y_offset = 125
    elif char in "()":
        y_offset = -55
    else:
        y_offset = 0

    pen = TTGlyphPen(None)
    height = mask.shape[0]
    for outline, depth in contours(mask):
        points = [(float(x) * scale + 45, (height - float(y)) * scale + y_offset) for x, y in outline]
        want_clockwise = depth % 2 == 0
        is_clockwise = signed_area(points) < 0
        if is_clockwise != want_clockwise:
            points.reverse()
        pen.moveTo(points[0])
        for point in points[1:]:
            pen.lineTo(point)
        pen.closePath()
    advance = max(220, int(mask.shape[1] * scale + 90))
    if char in "il.,:!":
        advance = max(170, int(mask.shape[1] * scale + 70))
    return pen.glyph(), advance


def build_font(extracted):
    char_order = list("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789äöüß.,:!?-+/&%()")
    glyph_order = [".notdef", "space"] + [safe_name(char) for char in char_order]
    built = {}
    metrics = {}

    notdef = TTGlyphPen(None)
    notdef.moveTo((80, 0)); notdef.lineTo((80, 680)); notdef.lineTo((520, 680))
    notdef.lineTo((520, 0)); notdef.closePath()
    built[".notdef"] = notdef.glyph()
    metrics[".notdef"] = (600, 0)
    built["space"] = TTGlyphPen(None).glyph()
    metrics["space"] = (280, 0)

    for char in char_order:
        variants = extracted[char]
        _, _, mask = variants[CANONICAL_VARIANT - 1]
        glyph, advance = glyph_from_mask(char, mask)
        name = safe_name(char)
        built[name] = glyph
        metrics[name] = (advance, 0)

    builder = FontBuilder(1000, isTTF=True)
    builder.setupGlyphOrder(glyph_order)
    builder.setupCharacterMap({ord(" "): "space", **{ord(c): safe_name(c) for c in char_order}})
    builder.setupGlyf(built)
    builder.setupHorizontalMetrics(metrics)
    builder.setupHorizontalHeader(ascent=820, descent=-230, lineGap=80)
    builder.setupOS2(
        sTypoAscender=820, sTypoDescender=-230, sTypoLineGap=80,
        usWinAscent=850, usWinDescent=250,
        sxHeight=500, sCapHeight=690, usWeightClass=400, usWidthClass=5,
    )
    builder.setupNameTable({
        "familyName": "CEOKlaue",
        "styleName": "Regular",
        "uniqueFontIdentifier": "Sammlr CEOKlaue v0.1",
        "fullName": "CEOKlaue Regular",
        "psName": "CEOKlaue-Regular",
        "version": "Version 0.1",
    })
    builder.setupPost(italicAngle=0, underlinePosition=-110, underlineThickness=45)
    builder.setupMaxp()
    ttf_path = FONT / "CEOKlaue-v0.1.ttf"
    builder.save(ttf_path)

    woff = TTFont(ttf_path)
    woff.flavor = "woff2"
    woff_path = FONT / "CEOKlaue-v0.1.woff2"
    woff.save(woff_path)
    RUNTIME.mkdir(parents=True, exist_ok=True)
    shutil.copy2(woff_path, RUNTIME / "ceoklaue-v0.1.woff2")
    return char_order


def write_manifests(chars):
    inventory = {
        "version": "CEOKlaue v0.1",
        "raw_sources": [SOURCES[key] for key in ("upper", "lower", "numbers", "codes")],
        "primary_sources": {
            "uppercase": SOURCES["upper"],
            "lowercase_and_symbols": SOURCES["lower"],
            "numbers": SOURCES["numbers"],
        },
        "style_and_legibility_reference": [SOURCES["numbers"], SOURCES["codes"]],
        "canonical_variant": CANONICAL_VARIANT,
        "included_characters": "".join(chars),
        "missing_requested_characters": "ÄÖÜ;",
        "signature_source_text": "Sammler.",
        "signature_runtime_status": "not shipped: source does not read Sammlr.",
        "public_runtime_assets": ["App/static/fonts/ceoklaue-v0.1.woff2"],
    }
    (FONT / "build-manifest.json").write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    actual = sorted(path.name for path in RAW.iterdir() if path.is_file())
    declared = sorted(SOURCES.values())
    missing = sorted(set(declared) - set(actual))
    unexpected = sorted(set(actual) - set(declared) - OPTIONAL_COMPLETION_SOURCES)
    if missing or unexpected:
        raise RuntimeError(
            f"00_raw inventory changed; missing={missing}, unexpected={unexpected}"
        )
    # These two trees are fully generated by this script.  Recreate them to
    # avoid stale variants after crop-map or naming changes.
    for generated_tree in (EXTRACTED / "glyphs", VECTORS / "glyphs"):
        if generated_tree.exists():
            shutil.rmtree(generated_tree)
    for directory in (EXTRACTED / "glyphs", VECTORS / "glyphs", FONT, SIGNATURE, RUNTIME):
        directory.mkdir(parents=True, exist_ok=True)
    extracted = extract_all()
    chars = build_font(extracted)
    write_manifests(chars)
    print(f"Built CEOKlaue v0.1 with {len(chars)} source-backed characters")


if __name__ == "__main__":
    main()
