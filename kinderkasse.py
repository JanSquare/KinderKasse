# kinderkasse.py
import asyncio
import serial_asyncio
from artikel_db import ArtikelDB
import vfd
from time import ctime

# Initialisiere Artikel-Datenbank und Display
artikel_db = ArtikelDB("artikel.csv")
display = vfd.BA63("/dev/ttySC0")
display.reset()
display.write("marloth automation", line=1, row=1)

# Steuer-Barcodes
STEUERCODE_BEZAHLEN = "9999999999998"
STEUERCODE_LOESCHEN = "9999999999999"

# Warenkorb als globale Liste
warenkorb = []

LINE_LENGTH = 20  # muss mit deinem Display-Modell übereinstimmen

class KassenScannerProtocol(asyncio.Protocol):
    def connection_made(self, transport):
        self.transport = transport
        print(f"[{ctime()}] Scanner verbunden")
        transport.serial.rts = False

    def data_received(self, data):
        code = data.decode(errors="ignore").strip()
        print(f"RAW: {data} | DECODED: {repr(code)}")

        if code == STEUERCODE_BEZAHLEN:
            self.bezahlen()
        elif code == STEUERCODE_LOESCHEN:
            self.loeschen()
        else:
            self.artikel_hinzufuegen(code)

    def artikel_hinzufuegen(self, code):
        artikel = artikel_db.suche(code)
        if artikel:
            zeile1, zeile2, preis = artikel
            warenkorb.append((zeile1, zeile2, preis))
            print(f"✔️  Hinzugefügt: {zeile1} | {zeile2} | {preis:.2f} EUR")
            display.clear()

            # Preis rechtsbündig, Text linksbündig — exakt LINE_LENGTH Zeichen
            preis_str = f"{preis:.2f}".replace(".", ",") + " EUR"
            max_len = LINE_LENGTH - len(preis_str)
            text_links = zeile1[:max_len].ljust(max_len)
            zeile1_komplett = text_links + preis_str

            display.write(zeile1_komplett, line=1, row=1)
            display.write(zeile2, line=2, row=1)
        else:
            print(f"❌ Artikel nicht gefunden für Barcode: {repr(code)}")
            display.clear()
            display.write("Unbekannter Code", line=1, row=1)

    def bezahlen(self):
        if not warenkorb:
            display.clear()
            display.write("Nichts zu zahlen", line=1, row=1)
            return

        display.clear()
        display.write("Summe:", line=1, row=1)
        gesamt = sum(preis for _, _, preis in warenkorb)
        display.write(f"{gesamt:.2f} EUR", line=2, row=1)

        print("🧾 Kassenbon:")
        for zeile1, zeile2, preis in warenkorb:
            print(f"  {zeile1} | {zeile2} | {preis:.2f} EUR")
        print(f"  Gesamtbetrag: {gesamt:.2f} EUR")
        warenkorb.clear()

    def loeschen(self):
        warenkorb.clear()
        print("🗑️ Warenkorb gelöscht")
        display.clear()
        display.write("Warenkorb", line=1, row=1)
        display.write("gelöscht", line=2, row=1)

    def connection_lost(self, exc):
        print(f"[{ctime()}] Scanner getrennt")
        loop.stop()

# Starte asyncio Eventloop
loop = asyncio.get_event_loop()
coro = serial_asyncio.create_serial_connection(
    loop, KassenScannerProtocol, '/dev/ttyACM0', baudrate=9600
)
transport, protocol = loop.run_until_complete(coro)
try:
    loop.run_forever()
except KeyboardInterrupt:
    print("Programm beendet")
finally:
    loop.close()