def codes(prefix, amount):
    return [f"{prefix} {i}" for i in range(1, amount + 1)]


def specials_for_team(prefix, full_team=True):
    if full_team:
        return [
            f"{prefix} SP",
            f"{prefix} PTW",
            f"{prefix} TOP 1",
            f"{prefix} TOP 2",
        ]
    else:
        return [
            f"{prefix} SP",
        ]


sections = []

sections.append(("Intro", codes("UEFA", 3) + codes("EURO", 11) + codes("MM", 2)))

groups = {
    "Group A": {
        "group_code": "GA",
        "full": ["GER", "SCO", "HUN", "SUI"],
        "short": []
    },
    "Group B": {
        "group_code": "GB",
        "full": ["ESP", "CRO", "ITA", "ALB"],
        "short": []
    },
    "Group C": {
        "group_code": "GC",
        "full": ["SLO", "DEN", "SRB", "ENG"],
        "short": []
    },
    "Group D": {
        "group_code": "GD",
        "full": ["FRA", "NED", "AUT"],
        "short": ["POL", "WAL", "FIN", "EST"]
    },
    "Group E": {
        "group_code": "GE",
        "full": ["BEL", "SVK", "ROU"],
        "short": ["UKR", "ISR", "BIH", "ICE"]
    },
    "Group F": {
        "group_code": "GF",
        "full": ["TUR", "GEO", "POR"],
        "short": ["CZE", "GRE", "KAZ", "LUX"]
    }
}


for group_name, data in groups.items():
    sticker = []

    sticker += codes(data["group_code"], 2)

    for team in data["full"]:
        sticker += codes(team, 21)
        sticker += [f"{team} P1", f"{team} P2"]
        sticker += specials_for_team(team, True)

    for team in data["short"]:
        sticker += codes(team, 15)
        sticker += specials_for_team(team, False)

    sections.append((group_name, sticker))


sections.append(("Legends", codes("LEG", 10)))


gesamt = 0

for name, sticker in sections:
    print()
    print(name)
    print("Anzahl:", len(sticker))
    gesamt += len(sticker)

print()
print("GESAMT:", gesamt)
print("ZIEL:", 707)
print("DIFFERENZ:", 707 - gesamt)