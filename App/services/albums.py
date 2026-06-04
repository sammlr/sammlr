from em24_data import build_em24
from wm26_data import build_wm26

def compact(text):
    return text.upper().replace(" ", "").replace("-", "")


def display_code(code):
    return code.replace(" ", "")

def em_map():
    mapping = {}
    for sticker in build_em24():
        mapping[compact(sticker["id"])] = sticker["id"]
        for slot in sticker["slots"]:
            mapping[compact(slot)] = sticker["id"]
    return mapping


def resolve_code(album_id, raw):

    value = raw.strip().upper()

    if album_id == "vfl":

        if not value.isdigit():
            return None

        if value not in all_codes("vfl"):
            return None

        return value

    if album_id == "wm26":
        cleaned = compact(value)
        wm_codes = {compact(s["id"]): s["id"] for s in build_wm26()}

        if cleaned not in wm_codes:
            return None

        return wm_codes[cleaned]

    mapping = em_map()

    cleaned = compact(value)

    if cleaned not in mapping:
        return None

    return mapping[cleaned]

def all_codes(album_id):
    if album_id == "vfl":
        return [str(i) for i in range(1, 251)]
    if album_id == "wm26":
        return [s["id"] for s in build_wm26()]
    return [s["id"] for s in build_em24()]
