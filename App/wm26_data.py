WM26_TEAMS = [
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

def build_wm26():
    stickers = []

    for i in range(1, 20):
        stickers.append({
            "id": f"FWC{i}",
            "section": "FIFA World Cup 2026"
        })

    for team in WM26_TEAMS:
        for i in range(1, 21):
            stickers.append({
                "id": f"{team}{i}",
                "section": team
            })

    for i in range(1, 13):
        stickers.append({
            "id": f"CC{i}",
            "section": "Coca-Cola"
        })

    return stickers