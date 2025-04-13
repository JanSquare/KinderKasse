# pflege_tool.py
import csv

ARTIKEL_DATEI = "artikel.csv"
UNBEKANNTE_DATEI = "unbekannte_barcodes.txt"

# Lade unbekannte Barcodes
with open(UNBEKANNTE_DATEI, "r", encoding="utf-8") as f:
    unbekannte = [line.strip() for line in f if line.strip()]

if not unbekannte:
    print("Keine unbekannten Barcodes vorhanden.")
    exit(0)

# Öffne Artikeldatenbank zum Anhängen
with open(ARTIKEL_DATEI, "a", newline='', encoding="utf-8") as csvfile:
    writer = csv.writer(csvfile, delimiter=';')

    bearbeitet = []

    for barcode in unbekannte:
        print(f"\nBarcode: {barcode}")
        zeile1 = input("Zeile 1: ").strip()
        zeile2 = input("Zeile 2: ").strip()
        preis_input = input("Preis (z. B. 1.29): ").strip().replace(",", ".")
        try:
            preis = float(preis_input)
        except ValueError:
            print("❌ Ungültiger Preis. Artikel wird übersprungen.")
            continue

        writer.writerow([barcode, zeile1, zeile2, f"{preis:.2f}"])
        bearbeitet.append(barcode)
        print("✔️ Artikel hinzugefügt.")

# Entferne bearbeitete Barcodes aus Datei
if bearbeitet:
    with open(UNBEKANNTE_DATEI, "w", encoding="utf-8") as f:
        for code in unbekannte:
            if code not in bearbeitet:
                f.write(code + "\n")

print("\nPflege abgeschlossen.")
