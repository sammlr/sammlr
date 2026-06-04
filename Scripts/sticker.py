# Stickeralbum Version 0.3 😄

# Daten laden
datei = open("fehlende.txt", "r")
fehlende = eval(datei.read())
datei.close()

try:
    datei = open("doppelte.txt", "r")
    doppelte = eval(datei.read())
    datei.close()
except:
    doppelte = []

while True:
    print("\n--- STICKERALBUM MENÜ ---")
    print("1 = Übersicht")
    print("2 = Sticker eintragen")
    print("3 = Doppelte anzeigen")
    print("4 = Beenden")

    auswahl = input("Was möchtest du machen? ")

    if auswahl == "1":
        vorhandene = []

        for sticker in range(1, 251):
            if sticker not in fehlende:
                vorhandene.append(sticker)

        print("\nDu hast", len(vorhandene), "von 250 Stickern 😄")
        print("Fehlende Sticker:", fehlende)

    if auswahl == "2":
        print("\n--- STICKER EINTRAGEN ---")
        print("Gib eine Stickernummer ein.")
        print("Oder tippe x, um zurück ins Hauptmenü zu gehen.")

        while True:
            eingabe = input("Stickernummer: ")

            if eingabe == "x":
                print("Zurück ins Hauptmenü 😄")
                break

            sticker = int(eingabe)

            if sticker in fehlende:
                fehlende.remove(sticker)
                print("Neuer Sticker fürs Album 🚀")
            else:
                doppelte.append(sticker)
                print("Doppelt 😎")

            datei = open("fehlende.txt", "w")
            datei.write(str(fehlende))
            datei.close()

            datei = open("doppelte.txt", "w")
            datei.write(str(doppelte))
            datei.close()
    if auswahl == "3":
        print("\n--- DOPPELTE STICKER ---")

        if len(doppelte) == 0:
            print("Du hast keine doppelten Sticker 😄")

        else:
            gezählt = {}

            for sticker in doppelte:

                if sticker in gezählt:
                    gezählt[sticker] = gezählt[sticker] + 1

                else:
                    gezählt[sticker] = 1

            for sticker in sorted(gezählt):
                print("Sticker", sticker, "=", gezählt[sticker], "x doppelt")

    if auswahl == "4":
        print("Bis später 😄")
        break