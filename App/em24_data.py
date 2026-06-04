def single(code, section):
    return {"id": code, "slots": [code], "section": section}


def big_team(prefix, section):
    codes = [f"{prefix} P1", f"{prefix} P2"]
    codes += [f"{prefix} {i}" for i in range(1, 22)]
    codes += [f"{prefix} PTW", f"{prefix} SP", f"{prefix} TOP1", f"{prefix} TOP2"]
    return [single(code, section) for code in codes]


def small_team(prefix, section):
    return [
        single(f"{prefix} 1", section),
        {"id": f"{prefix} 2/3", "slots": [f"{prefix} 2", f"{prefix} 3"], "section": section},
        {"id": f"{prefix} 4/5", "slots": [f"{prefix} 4", f"{prefix} 5"], "section": section},
        {"id": f"{prefix} 6/7", "slots": [f"{prefix} 6", f"{prefix} 7"], "section": section},
        {"id": f"{prefix} 8/9", "slots": [f"{prefix} 8", f"{prefix} 9"], "section": section},
        {"id": f"{prefix} 10/11", "slots": [f"{prefix} 10", f"{prefix} 11"], "section": section},
        {"id": f"{prefix} 12/13", "slots": [f"{prefix} 12", f"{prefix} 13"], "section": section},
        {"id": f"{prefix} 14/15", "slots": [f"{prefix} 14", f"{prefix} 15"], "section": section},
    ]


def shared_sp(a, b, section):
    return {"id": f"{a}/{b} SP", "slots": [f"{a} SP", f"{b} SP"], "section": section}


def group_banner(group_code, section):
    return [
        single(f"{group_code}1", section),
        single(f"{group_code}2", section),
    ]


def build_em24():
    stickers = []

    stickers += [single("TOPPS 1", "Intro")]
    stickers += [single(f"UEFA {i}", "Intro") for i in range(1, 4)]
    stickers += [single(f"EURO {i}", "Intro") for i in range(1, 12)]

    abc_groups = {
        "Group A": ("GA", ["GER", "SCO", "HUN", "SUI"]),
        "Group B": ("GB", ["ESP", "CRO", "ITA", "ALB"]),
        "Group C": ("GC", ["SLO", "DEN", "SRB", "ENG"]),
    }

    for section, (group_code, teams) in abc_groups.items():
        stickers += group_banner(group_code, section)
        for team in teams:
            stickers += big_team(team, section)

    def_groups = {
        "Group D": {
            "code": "GD",
            "big": ["NED", "AUT", "FRA"],
            "small": ["POL", "EST", "WAL", "FIN"],
            "sp_pairs": [("POL", "WAL"), ("EST", "FIN")],
        },
        "Group E": {
            "code": "GE",
            "big": ["BEL", "SVK", "ROU"],
            "small": ["ISR", "ICE", "BIH", "UKR"],
            "sp_pairs": [("ISR", "ICE"), ("BIH", "UKR")],
        },
        "Group F": {
            "code": "GF",
            "big": ["TUR", "POR", "CZE"],
            "small": ["GEO", "LUX", "GRE", "KAZ"],
            "sp_pairs": [("GEO", "LUX"), ("GRE", "KAZ")],
        },
    }

    for section, data in def_groups.items():
        stickers += group_banner(data["code"], section)

        for team in data["big"]:
            stickers += big_team(team, section)

        for team in data["small"]:
            stickers += small_team(team, section)

        for a, b in data["sp_pairs"]:
            stickers.append(shared_sp(a, b, section))

    stickers.append({"id": "MM 1/2", "slots": ["MM 1", "MM 2"], "section": "Dream Team"})

    stickers += [single(f"LEG {i}", "Legends") for i in range(1, 11)]

    return stickers


if __name__ == "__main__":
    stickers = build_em24()
    slots = []

    for sticker in stickers:
        slots += sticker["slots"]

    print("Physische Sticker:", len(stickers))
    print("Album-Slots:", len(slots))