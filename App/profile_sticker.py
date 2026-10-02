"""Data and rendering contract for the configurable 1970s profile sticker."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import secrets
import sqlite3
import struct
import zlib

from flask import render_template


@dataclass(frozen=True)
class ProfileStickerCountry:
    code: str
    label: str
    flag_bands: tuple[str, str, str]


@dataclass(frozen=True)
class ProfileStickerColor:
    code: str
    label: str
    hex_value: str
    contrast: str


@dataclass(frozen=True)
class ProfileStickerSettings:
    user_id: int
    display_name: str
    country_code: str
    club_name: str
    accent_color: str
    portrait_filename: str | None
    portrait_mime: str | None
    crop_x: float
    crop_y: float
    crop_zoom: float
    portrait_width: int | None = None
    portrait_height: int | None = None


PROFILE_STICKER_NATION_LIGHT_BLUE = "#5DA9D6"


PROFILE_STICKER_COUNTRIES = {
    "DE": ProfileStickerCountry("DE", "DEUTSCHLAND", ("#171717", "#D22630", "#F4C430")),
    "NL": ProfileStickerCountry("NL", "NIEDERLANDE", ("#AE1C28", "#FFFFFF", "#21468B")),
    "FR": ProfileStickerCountry("FR", "FRANKREICH", ("#0055A4", "#FFFFFF", "#EF4135")),
    "IT": ProfileStickerCountry("IT", "ITALIEN", ("#009246", "#FFFFFF", "#CE2B37")),
    "BE": ProfileStickerCountry("BE", "BELGIEN", ("#171717", "#F9D616", "#EF3340")),
    "IE": ProfileStickerCountry("IE", "IRLAND", ("#169B62", "#FFFFFF", "#FF883E")),
    "RO": ProfileStickerCountry("RO", "RUMÄNIEN", ("#002B7F", "#FCD116", "#CE1126")),
    "AT": ProfileStickerCountry("AT", "ÖSTERREICH", ("#ED2939", "#FFFFFF", "#ED2939")),
    "ES": ProfileStickerCountry("ES", "SPANIEN", ("#AA151B", "#F1BF00", "#AA151B")),
    "AR": ProfileStickerCountry("AR", "ARGENTINIEN", (PROFILE_STICKER_NATION_LIGHT_BLUE, "#FFFFFF", PROFILE_STICKER_NATION_LIGHT_BLUE)),
    "EG": ProfileStickerCountry("EG", "ÄGYPTEN", ("#CE1126", "#FFFFFF", "#171717")),
    "HU": ProfileStickerCountry("HU", "UNGARN", ("#CE2939", "#FFFFFF", "#477050")),
    "BG": ProfileStickerCountry("BG", "BULGARIEN", ("#FFFFFF", "#00966E", "#D62612")),
    "LU": ProfileStickerCountry("LU", "LUXEMBURG", ("#EF3340", "#FFFFFF", PROFILE_STICKER_NATION_LIGHT_BLUE)),
    "RU": ProfileStickerCountry("RU", "RUSSLAND", ("#FFFFFF", "#0039A6", "#D52B1E")),
    "CO": ProfileStickerCountry("CO", "KOLUMBIEN", ("#FCD116", "#003893", "#CE1126")),
    "MX": ProfileStickerCountry("MX", "MEXIKO", ("#006847", "#FFFFFF", "#CE1126")),
    "PE": ProfileStickerCountry("PE", "PERU", ("#D91023", "#FFFFFF", "#D91023")),
    "TH": ProfileStickerCountry("TH", "THAILAND", ("#A51931", "#FFFFFF", "#2D2A4A")),
}

PROFILE_STICKER_COLORS = {
    "purple": ProfileStickerColor("purple", "Lila", "#6F35A5", "light"),
    "red": ProfileStickerColor("red", "Rot", "#C83C43", "light"),
    "blue": ProfileStickerColor("blue", "Blau", "#285DA8", "light"),
    "yellow": ProfileStickerColor("yellow", "Gelb", "#F2C84B", "dark"),
    "green": ProfileStickerColor("green", "Grün", "#3E7D55", "light"),
    "orange": ProfileStickerColor("orange", "Orange", "#DF762D", "dark"),
    "black": ProfileStickerColor("black", "Schwarz", "#242220", "light"),
    "cream": ProfileStickerColor("cream", "Weiß / Creme", "#F4EBDD", "dark"),
}

MAX_DISPLAY_NAME_LENGTH = 32
MAX_CLUB_NAME_LENGTH = 48
MAX_PORTRAIT_BYTES = 900 * 1024
MIN_CROP_POSITION = -35.0
MAX_CROP_POSITION = 35.0
MIN_CROP_ZOOM = 1.0
MAX_CROP_ZOOM = 2.5
SAFE_PORTRAIT_NAME = re.compile(r"^[a-f0-9]{32}\.(?:jpg|png)$")


class ProfileStickerValidationError(ValueError):
    pass


def schema_available(connection: sqlite3.Connection) -> bool:
    return connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='user_profile_stickers'"
    ).fetchone() is not None


def _clean_text(value: str | None, *, maximum: int, required: bool = False) -> str:
    clean = " ".join((value or "").split())
    if required and not clean:
        raise ProfileStickerValidationError("Bitte einen Stickernamen eingeben.")
    if len(clean) > maximum:
        raise ProfileStickerValidationError("Die Eingabe ist zu lang.")
    return clean


def validate_settings(display_name, country_code, club_name, accent_color, crop_x, crop_y, crop_zoom):
    name = _clean_text(display_name, maximum=MAX_DISPLAY_NAME_LENGTH, required=True)
    club = _clean_text(club_name, maximum=MAX_CLUB_NAME_LENGTH)
    country = (country_code or "").strip().upper()
    accent = (accent_color or "").strip().lower()
    if country not in PROFILE_STICKER_COUNTRIES:
        raise ProfileStickerValidationError("Diese Nation wird noch nicht unterstützt.")
    if accent not in PROFILE_STICKER_COLORS:
        raise ProfileStickerValidationError("Diese Farbe wird nicht unterstützt.")
    try:
        x, y, zoom = float(crop_x), float(crop_y), float(crop_zoom)
    except (TypeError, ValueError) as error:
        raise ProfileStickerValidationError("Der Fotoausschnitt ist ungültig.") from error
    if not (MIN_CROP_POSITION <= x <= MAX_CROP_POSITION):
        raise ProfileStickerValidationError("Der horizontale Fotoausschnitt ist ungültig.")
    if not (MIN_CROP_POSITION <= y <= MAX_CROP_POSITION):
        raise ProfileStickerValidationError("Der vertikale Fotoausschnitt ist ungültig.")
    if not (MIN_CROP_ZOOM <= zoom <= MAX_CROP_ZOOM):
        raise ProfileStickerValidationError("Der Foto-Zoom ist ungültig.")
    return name, country, club, accent, round(x, 2), round(y, 2), round(zoom, 3)


def load_settings(connection: sqlite3.Connection, user_id: int, fallback_name: str) -> ProfileStickerSettings:
    fallback = _clean_text(fallback_name, maximum=MAX_DISPLAY_NAME_LENGTH) or "SAMMLR"
    if not schema_available(connection):
        return ProfileStickerSettings(user_id, fallback, "DE", "", "purple", None, None, 0, 0, 1)
    row = connection.execute(
        """SELECT user_id, display_name, country_code, club_name, accent_color,
                  portrait_filename, portrait_mime, crop_x, crop_y, crop_zoom,
                  portrait_width, portrait_height
           FROM user_profile_stickers WHERE user_id=?""",
        (user_id,),
    ).fetchone()
    if row is None:
        return ProfileStickerSettings(user_id, fallback, "DE", "", "purple", None, None, 0, 0, 1)
    return ProfileStickerSettings(
        int(row[0]), row[1], row[2], row[3] or "", row[4], row[5], row[6],
        float(row[7]), float(row[8]), float(row[9]), row[10], row[11],
    )


def save_settings(connection: sqlite3.Connection, settings: ProfileStickerSettings) -> None:
    connection.execute(
        """INSERT INTO user_profile_stickers
               (user_id, display_name, country_code, club_name, accent_color,
                portrait_filename, portrait_mime, crop_x, crop_y, crop_zoom,
                portrait_width, portrait_height, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
           ON CONFLICT(user_id) DO UPDATE SET
               display_name=excluded.display_name,
               country_code=excluded.country_code,
               club_name=excluded.club_name,
               accent_color=excluded.accent_color,
               portrait_filename=excluded.portrait_filename,
               portrait_mime=excluded.portrait_mime,
               crop_x=excluded.crop_x,
               crop_y=excluded.crop_y,
               crop_zoom=excluded.crop_zoom,
               portrait_width=excluded.portrait_width,
               portrait_height=excluded.portrait_height,
               updated_at=CURRENT_TIMESTAMP""",
        (
            settings.user_id, settings.display_name, settings.country_code,
            settings.club_name, settings.accent_color, settings.portrait_filename,
            settings.portrait_mime, settings.crop_x, settings.crop_y, settings.crop_zoom,
            settings.portrait_width, settings.portrait_height,
        ),
    )


def _jpeg_dimensions(data: bytes) -> tuple[int, int] | None:
    index = 2
    while index + 9 < len(data):
        if data[index] != 0xFF:
            index += 1
            continue
        marker = data[index + 1]
        index += 2
        if marker in {0xD8, 0xD9} or 0xD0 <= marker <= 0xD7:
            continue
        if index + 2 > len(data):
            return None
        length = int.from_bytes(data[index:index + 2], "big")
        if length < 2 or index + length > len(data):
            return None
        if marker in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}:
            if length < 7:
                return None
            return int.from_bytes(data[index + 5:index + 7], "big"), int.from_bytes(data[index + 3:index + 5], "big")
        index += length
    return None


def _png_chunks(data: bytes):
    index = 8
    while index + 12 <= len(data):
        length = int.from_bytes(data[index:index + 4], "big")
        end = index + 12 + length
        if length > len(data) or end > len(data):
            raise ProfileStickerValidationError("Die PNG-Datei ist beschädigt.")
        chunk_type = data[index + 4:index + 8]
        payload = data[index + 8:index + 8 + length]
        expected_crc = int.from_bytes(data[index + 8 + length:end], "big")
        if zlib.crc32(chunk_type + payload) & 0xFFFFFFFF != expected_crc:
            raise ProfileStickerValidationError("Die PNG-Datei ist beschädigt.")
        yield chunk_type, payload
        index = end
        if chunk_type == b"IEND":
            if index != len(data):
                raise ProfileStickerValidationError("Die PNG-Datei enthält ungültige Zusatzdaten.")
            return
    raise ProfileStickerValidationError("Die PNG-Datei ist unvollständig.")


def _sanitise_png(data: bytes) -> bytes:
    output = bytearray(data[:8])
    seen_idat = False
    chunks = tuple(_png_chunks(data))
    if not chunks or chunks[0][0] != b"IHDR" or chunks[-1][0] != b"IEND":
        raise ProfileStickerValidationError("Die PNG-Datei ist beschädigt.")
    for chunk_type, payload in chunks:
        if chunk_type == b"IDAT":
            seen_idat = True
        if chunk_type in {b"tEXt", b"zTXt", b"iTXt", b"eXIf", b"tIME"}:
            continue
        output.extend(len(payload).to_bytes(4, "big"))
        output.extend(chunk_type)
        output.extend(payload)
        output.extend((zlib.crc32(chunk_type + payload) & 0xFFFFFFFF).to_bytes(4, "big"))
    if not seen_idat:
        raise ProfileStickerValidationError("Die PNG-Datei enthält keine Bilddaten.")
    return bytes(output)


def _sanitise_jpeg(data: bytes) -> bytes:
    if not data.endswith(b"\xff\xd9"):
        raise ProfileStickerValidationError("Die JPEG-Datei ist unvollständig.")
    output = bytearray(data[:2])
    index = 2
    while index + 4 <= len(data):
        if data[index] != 0xFF:
            raise ProfileStickerValidationError("Die JPEG-Datei ist beschädigt.")
        marker_start = index
        while index < len(data) and data[index] == 0xFF:
            index += 1
        marker = data[index]
        index += 1
        if marker == 0xDA:
            output.extend(data[marker_start:])
            return bytes(output)
        if marker == 0xD9:
            output.extend(b"\xff\xd9")
            return bytes(output)
        if 0xD0 <= marker <= 0xD7 or marker == 0x01:
            output.extend(data[marker_start:index])
            continue
        if index + 2 > len(data):
            break
        length = int.from_bytes(data[index:index + 2], "big")
        end = index + length
        if length < 2 or end > len(data):
            break
        if marker not in {0xE1, 0xED, 0xFE}:
            output.extend(data[marker_start:end])
        index = end
    raise ProfileStickerValidationError("Die JPEG-Datei ist beschädigt.")


def inspect_portrait(data: bytes) -> tuple[str, str, int, int]:
    if not data or len(data) > MAX_PORTRAIT_BYTES:
        raise ProfileStickerValidationError("Das Foto ist leer oder größer als 900 KB.")
    if data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) >= 24 and data[12:16] == b"IHDR":
        _sanitise_png(data)
        width, height = struct.unpack(">II", data[16:24])
        mime, extension = "image/png", "png"
    elif data.startswith(b"\xff\xd8\xff"):
        dimensions = _jpeg_dimensions(data)
        if dimensions is None:
            raise ProfileStickerValidationError("Die JPEG-Datei ist beschädigt.")
        width, height = dimensions
        mime, extension = "image/jpeg", "jpg"
    else:
        raise ProfileStickerValidationError("Bitte ein echtes JPEG- oder PNG-Bild auswählen.")
    if width < 1 or height < 1 or width > 8000 or height > 8000 or width * height > 40_000_000:
        raise ProfileStickerValidationError("Die Bildabmessungen werden nicht unterstützt.")
    return mime, extension, width, height


def store_portrait(data: bytes, storage_dir: Path) -> tuple[str, str, int, int]:
    mime, extension, width, height = inspect_portrait(data)
    safe_data = _sanitise_png(data) if extension == "png" else _sanitise_jpeg(data)
    storage_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{secrets.token_hex(16)}.{extension}"
    destination = storage_dir / filename
    destination.write_bytes(safe_data)
    return filename, mime, width, height


def remove_portrait(storage_dir: Path, filename: str | None) -> None:
    if not filename or SAFE_PORTRAIT_NAME.fullmatch(filename) is None:
        return
    path = storage_dir / filename
    if path.is_file():
        path.unlink()


def _name_scale_class(name: str) -> str:
    length = len(name)
    if length <= 7:
        return "is-short"
    if length <= 14:
        return "is-medium"
    if length <= 22:
        return "is-long"
    return "is-extra-long"


def render_profile_sticker(
    settings: ProfileStickerSettings,
    *,
    editor: bool = False,
    portrait_url: str | None = None,
) -> str:
    country = PROFILE_STICKER_COUNTRIES.get(settings.country_code, PROFILE_STICKER_COUNTRIES["DE"])
    color = PROFILE_STICKER_COLORS.get(settings.accent_color, PROFILE_STICKER_COLORS["purple"])
    portrait_url = portrait_url or (
        f"/profil/sticker/portrait/{settings.portrait_filename}"
        if settings.portrait_filename else (
            "data:image/svg+xml,%3Csvg%20xmlns=%22http://www.w3.org/2000/svg%22%20"
            "width=%221%22%20height=%221%22%3E%3C/svg%3E"
        )
    )
    return render_template(
        "components/profile_sticker_70.html",
        settings=settings,
        country=country,
        color=color,
        portrait_url=portrait_url,
        name_scale_class=_name_scale_class(settings.display_name),
        editor=editor,
    )
