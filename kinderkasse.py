# kinderkasse.py
import asyncio
import serial_asyncio
from artikel_db import ArtikelDB
import vfd
from time import ctime, strftime, sleep
import os
import threading

# Barcode Scanner
SCANNER_DEVICE = '/dev/serial/by-id/usb-SM_SM-2D_PRODUCT_USB_UART_APP-000000000-if00'

# Initialisiere Artikel-Datenbank und Display
artikel_db = ArtikelDB("artikel.csv")
display = vfd.BA63("/dev/ttySC0")
LINE_LENGTH = 20

# Steuer-Barcodes
STEUERCODE_BEZAHLEN = "9999999999998"
STEUERCODE_LOESCHEN = "9999999999999"

# Warenkorb als globale Liste
warenkorb = []

# Liste nicht gefundener Barcodes
UNBEKANNTE_DATEI = "unbekannte_barcodes.txt"
if os.path.exists(UNBEKANNTE_DATEI):
    with open(UNBEKANNTE_DATEI, "r", encoding="utf-8") as f:
        unbekannte_barcodes = set(line.strip() for line in f if line.strip())
else:
    unbekannte_barcodes = set()

# Belegdruck über Epson TM-T20II
BON_WIDTH = 48

ASCII_LOGO = (
    " ___    _____  ___    ___    _____  ___         "
    "(  _`\ (  _  )(  _`\ (  _`\ (  _  )|  _`\       "
    "| ( (_)| (_) || (_(_)| |_) )| (_) || (_) )  ___ "
    "| |  _ |  _  |`\__ \ | ,__/'|  _  || ,  / /',__)"
    "| (_( )| | | |( )_) || |    | | | || |\ \ \__, \\" 
    "(____/'(_) (_)`\____)(_)    (_) (_)(_) (_)(____/"
    "                                                "
    " _      _____  ___    ___    _   _              "
    "( )    (  _  )(  _`\ (  _`\ ( ) ( )             "
    "| |    | (_) || | ) || (_(_)| `\| |             "
    "| |  _ |  _  || | | )|  _)_ | , ` |             "
    "| |_( )| | | || |_) || (_( )| |`\ |             "
    "(____/'(_) (_)(____/'(____/'(_) (_)             "
    "                                                "
)

def zeige_schoner():
    display.clear()
    display.write("CASPARs Laden", line=1, row=1)
    display.write(strftime("%d.%m.%Y %H:%M"), line=2, row=1)

def verzögert_schoner():
    threading.Timer(10.0, zeige_schoner).start()

def drucke_bon(positionen, gesamt):
    try:
        with open("/dev/usb/lp0", "w", encoding="cp437") as drucker:
            drucker.write("\n" + ASCII_LOGO + "\n")
            drucker.write("=" * BON_WIDTH + "\n")
            drucker.write("\n")
            drucker.write("Bestellung:\n")
            drucker.write("-" * BON_WIDTH + "\n")
            for zeile1, zeile2, preis in positionen:
                preis_str = f"{preis:.2f} EUR"
                max_len = BON_WIDTH - len(preis_str)
                text_links = zeile1[:max_len].ljust(max_len)
                drucker.write(f"{text_links}{preis_str}\n")
                drucker.write(f"{zeile2}\n")
                drucker.write("\n")
            drucker.write("-" * BON_WIDTH + "\n")
            drucker.write(f"GESAMT: {gesamt:.2f} EUR\n")
            drucker.write("=" * BON_WIDTH + "\n")
            drucker.write("Vielen Dank für deinen Einkauf!\n")
            drucker.write("\n")
            drucker.write("\n")
            drucker.write("\n\n\n\x1D\x56\x00")
    except Exception as e:
        print(f"❌ Fehler beim Drucken: {e}")

class KassenScannerProtocol(asyncio.Protocol):
    def connection_made(self, transport):
        self.transport = transport
        print(f"[{ctime()}] Scanner verbunden")
        transport.serial.rts = False

    def data_received(self, data):
        global artikel_db
        code = data.decode(errors="ignore").strip()
        print(f"RAW: {data} | DECODED: {repr(code)}")

        # CSV nach jedem Scan neu laden
        artikel_db = ArtikelDB("artikel.csv")

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

            preis_str = f"{preis:.2f}".replace(".", ",") + " EUR"
            max_len = LINE_LENGTH - len(preis_str)
            text_links = zeile1[:max_len].ljust(max_len)
            zeile1_komplett = text_links + preis_str

            display.write(zeile1_komplett, line=1, row=1)
            display.write(zeile2, line=2, row=1)
        else:
            if code not in unbekannte_barcodes:
                unbekannte_barcodes.add(code)
                try:
                    with open(UNBEKANNTE_DATEI, "a", encoding="utf-8") as f:
                        f.write(code + "\n")
                except Exception as e:
                    print(f"Fehler beim Schreiben in {UNBEKANNTE_DATEI}: {e}")

            print(f"❌ Artikel nicht gefunden für Barcode: {repr(code)}")
            display.clear()
            display.write("Unbekannter Code", line=1, row=1)
            display.write(code, line=2, row=1)

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

        drucke_bon(warenkorb, gesamt)
        warenkorb.clear()
        verzögert_schoner()

    def loeschen(self):
        warenkorb.clear()
        print("🗑️ Warenkorb gelöscht")
        display.clear()
        display.write("Warenkorb", line=1, row=1)
        display.write("gelöscht", line=2, row=1)

    def connection_lost(self, exc):
        print(f"[{ctime()}] Scanner getrennt")
        loop.stop()

# Starte mit Bildschirmschoner
zeige_schoner()

# Starte asyncio Eventloop
loop = asyncio.get_event_loop()
coro = serial_asyncio.create_serial_connection(
    loop, KassenScannerProtocol, SCANNER_DEVICE, baudrate=9600
)
transport, protocol = loop.run_until_complete(coro)
try:
    loop.run_forever()
except KeyboardInterrupt:
    print("Programm beendet")
finally:
    loop.close()
