import csv

ARTIKEL_DATEI = "artikel.csv"

class ArtikelDB:
    def __init__(self, pfad=ARTIKEL_DATEI):
        self.pfad = pfad
        self.artikel = {}  # barcode → (zeile1, zeile2, preis)
        self._lade_daten()

    def _lade_daten(self):
        try:
            with open(self.pfad, newline='', encoding="utf-8") as f:
                reader = csv.DictReader(f, delimiter=';')
                for zeile in reader:
                    barcode = zeile["Barcode"].strip()
                    zeile1 = zeile["Zeile1"].strip()
                    zeile2 = zeile["Zeile2"].strip()
                    preis = float(zeile["Preis"].replace(",", "."))
                    self.artikel[barcode] = (zeile1, zeile2, preis)
        except FileNotFoundError:
            print(f"⚠️ Datei {self.pfad} nicht gefunden.")
        except Exception as e:
            print(f"❌ Fehler beim Laden der CSV: {e}")

    def suche(self, barcode):
        return self.artikel.get(barcode, None)

    def refresh(self):
        """Leert den Cache und lädt die Datenbank neu."""
        self.artikel.clear()
        self._lade_daten()
