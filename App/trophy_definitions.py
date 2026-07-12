GLOBAL_SCOPE = "__global__"

GLOBAL_STICKER_THRESHOLDS = [50, 100, 250, 500, 1000, 2500, 5000, 10000, 25000]
GLOBAL_DUPLICATE_THRESHOLDS = [50, 100, 250, 500, 1000, 2500, 5000, 10000, 25000]
GLOBAL_TRADE_THRESHOLDS = [1, 10, 25, 50, 100, 250]

WM26_TEAM_ORDER = [
    "MEX", "RSA", "KOR", "CZE",
    "CAN", "BIH", "QAT", "SUI",
    "BRA", "MAR", "HAI", "SCO",
    "USA", "PAR", "AUS", "TUR",
    "GER", "CUW", "CIV", "ECU",
    "NED", "JPN", "SWE", "TUN",
    "BEL", "EGY", "IRN", "NZL",
    "ESP", "CPV", "KSA", "URU",
    "FRA", "SEN", "IRQ", "NOR",
    "ARG", "ALG", "AUT", "JOR",
    "POR", "COD", "UZB", "COL",
    "ENG", "CRO", "GHA", "PAN",
]

WM26_GROUP_NAMES = [
    "Gruppe A", "Gruppe B", "Gruppe C", "Gruppe D",
    "Gruppe E", "Gruppe F", "Gruppe G", "Gruppe H",
    "Gruppe I", "Gruppe J", "Gruppe K", "Gruppe L",
]

VFL_CHAPTERS = [
    ("Intro", 1, 2, "intro"),
    ("Kader & Staff", 3, 84, "vfl_squad"),
    ("Rückblick", 85, 95, "vfl_newspaper"),
    ("Schönste Tore", 96, 108, "vfl_goal"),
    ("Bremer Brücke", 109, 139, "vfl_floodlight"),
    ("Trikots", 140, 152, "vfl_shirt"),
    ("Choreos", 153, 170, "vfl_flag"),
    ("Historie", 171, 183, "book_open"),
    ("Legenden 11", 184, 195, "vfl_laurel"),
    ("Große Spieler", 196, 198, "vfl_player"),
    ("90+6", 199, 213, "vfl_906"),
    ("Eules letzter Flug", 214, 225, "vfl_owl"),
    ("Spiele für die Ewigkeit", 226, 244, "vfl_bicycle"),
    ("Fanshop", 245, 250, "vfl_bag"),
]


def trophy_id(scope, name, value=None):
    slug = (
        name.lower()
        .replace("&", "und")
        .replace("+", "plus")
        .replace("ä", "ae")
        .replace("ö", "oe")
        .replace("ü", "ue")
        .replace("ß", "ss")
    )
    slug = "".join(char if char.isalnum() else "_" for char in slug)
    while "__" in slug:
        slug = slug.replace("__", "_")
    slug = slug.strip("_")
    return f"{scope}:{slug}:{value}" if value is not None else f"{scope}:{slug}"


def make_trophy(scope, album_id, name, description, icon_key, trigger_type, trigger_value=None, codes=None):
    return {
        "id": trophy_id(album_id or scope, name, trigger_value),
        "scope": scope,
        "album_id": album_id,
        "name": name,
        "description": description,
        "icon_key": icon_key,
        "trigger_type": trigger_type,
        "trigger_value": trigger_value,
        "sticker_codes": codes or [],
    }


def global_trophy_definitions():
    trophies = []
    for value in GLOBAL_STICKER_THRESHOLDS:
        trophies.append(make_trophy(
            "global", None, f"Stickerjäger {value}",
            f"Sammle insgesamt {value} Sticker über alle Alben.",
            "global_sticker", "global_stickers", value
        ))
    for value in GLOBAL_DUPLICATE_THRESHOLDS:
        trophies.append(make_trophy(
            "global", None, f"Tauschmaterial {value}",
            f"Besitze insgesamt {value} doppelte Sticker über alle Alben.",
            "global_duplicates", "global_duplicates", value
        ))
    for value in GLOBAL_TRADE_THRESHOLDS:
        trophies.append(make_trophy(
            "global", None, f"Tauschgeschäfte {value}",
            f"Schließe {value} Tauschgeschäfte erfolgreich ab.",
            "global_trades", "global_trades", value
        ))
    return trophies


def wm26_group_codes(group_index):
    teams = WM26_TEAM_ORDER[group_index * 4:(group_index + 1) * 4]
    codes = []
    for team in teams:
        codes.extend([f"{team}{number}" for number in range(1, 21)])
    return codes


def wm26_trophy_definitions(total):
    half = max(total // 2, 1)
    trophies = [
        make_trophy("album", "wm26", "Erster Sticker", "Trage deinen ersten Sticker in dieses Album ein.", "first_sticker", "album_count", 1),
        make_trophy("album", "wm26", "Halbzeit", "Sammle die Hälfte aller Sticker dieses Albums.", "half_circle", "album_count", half),
        make_trophy("album", "wm26", "Endspurt", "Es fehlen nur noch 10 Sticker bis zum vollständigen Album.", "finish_line", "album_count", max(total - 10, 1)),
        make_trophy("album", "wm26", "Album vollendet", "Sammle alle Sticker dieses Albums.", "album_generic", "album_complete", total),
        make_trophy("album", "wm26", "Intro", "Sammle alle Intro-Sticker.", "book_open", "codes", codes=[f"FWC{i}" for i in range(1, 9)]),
    ]

    for index, group_name in enumerate(WM26_GROUP_NAMES):
        trophies.append(make_trophy(
            "album", "wm26", group_name,
            f"Sammle alle Sticker der {group_name}.",
            f"group_{chr(ord('a') + index)}", "codes", codes=wm26_group_codes(index)
        ))

    trophies.extend([
        make_trophy("album", "wm26", "Wappenexperte", "Sammle alle Länderwappen.", "shield_ball", "codes", codes=[f"{team}1" for team in WM26_TEAM_ORDER]),
        make_trophy("album", "wm26", "Teamfotograf", "Sammle alle Teamfotos.", "camera", "codes", codes=[f"{team}13" for team in WM26_TEAM_ORDER]),
        make_trophy("album", "wm26", "Historiker", "Sammle alle historischen Seiten.", "book_open", "codes", codes=[f"FWC{i}" for i in range(9, 20)]),
        make_trophy("album", "wm26", "Etikettenknibbler", "Sammle alle Coca-Cola-Sticker.", "coke_bottle", "codes", codes=[f"CC{i}" for i in range(1, 13)]),
        make_trophy("album", "wm26", "The Last Dance", "Sammle Messi (ARG17) und Cristiano Ronaldo (POR15).", "last_dance", "codes", codes=["ARG17", "POR15"]),
    ])
    return trophies


def vfl_codes(start, end):
    return [str(number) for number in range(start, end + 1)]


def vfl_trophy_definitions(total):
    half = max(total // 2, 1)
    trophies = [
        make_trophy("album", "vfl", "Erster Sticker", "Trage deinen ersten Sticker in dieses Album ein.", "first_sticker", "album_count", 1),
        make_trophy("album", "vfl", "Halbzeit", "Sammle die Hälfte aller Sticker dieses Albums.", "half_circle", "album_count", half),
        make_trophy("album", "vfl", "Endspurt", "Es fehlen nur noch 10 Sticker bis zum vollständigen Album.", "finish_line", "album_count", max(total - 10, 1)),
        make_trophy("album", "vfl", "Album vollendet", "Sammle alle Sticker dieses Albums.", "album_generic", "album_complete", total),
    ]
    for name, start, end, icon_key in VFL_CHAPTERS:
        trophies.append(make_trophy(
            "album", "vfl", name,
            f"Sammle alle Sticker aus {name}.",
            icon_key, "codes", codes=vfl_codes(start, end)
        ))
    trophies.append(make_trophy(
        "album", "vfl", "DJ Matze",
        "Sammle DJ Matze.",
        "vfl_record", "codes", codes=["124"]
    ))
    return trophies


def album_trophy_definitions(album_id, total):
    if album_id == "wm26":
        return wm26_trophy_definitions(total)
    if album_id == "vfl":
        return vfl_trophy_definitions(total)
    half = max(total // 2, 1)
    return [
        make_trophy("album", album_id, "Erster Sticker", "Trage deinen ersten Sticker in dieses Album ein.", "first_sticker", "album_count", 1),
        make_trophy("album", album_id, "Halbzeit", "Sammle die Hälfte aller Sticker dieses Albums.", "half_circle", "album_count", half),
        make_trophy("album", album_id, "Endspurt", "Es fehlen nur noch 10 Sticker bis zum vollständigen Album.", "finish_line", "album_count", max(total - 10, 1)),
        make_trophy("album", album_id, "Album vollendet", "Sammle alle Sticker dieses Albums.", "album_generic", "album_complete", total),
    ]
