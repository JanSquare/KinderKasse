import asyncio
import serial_asyncio
import logging
import os
import tempfile
from typing import List, Tuple, Set

from artikel_db import ArtikelDB
import vfd

# Barcode Scanner device
SCANNER_DEVICE = '/dev/serial/by-id/usb-SM_SM-2D_PRODUCT_USB_UART_APP-000000000-if00'

# Steuer-Barcodes
STEUERCODE_BEZAHLEN = "9999999999998"
STEUERCODE_LOESCHEN = "9999999999999"

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

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


def drucke_bon(positionen: List[Tuple[str, str, float]], gesamt: float) -> None:
    try:
        with open("/dev/usb/lp0", "w", encoding="cp437") as drucker:
            drucker.write("\n" + ASCII_LOGO + "\n")
            drucker.write("=" * BON_WIDTH + "\n")
            drucker.write("\nBestellung:\n")
            drucker.write("-" * BON_WIDTH + "\n")
            for zeile1, zeile2, preis in positionen:
                preis_str = f"{preis:.2f} EUR"
                max_len = BON_WIDTH - len(preis_str)
                text_links = zeile1[:max_len].ljust(max_len)
                drucker.write(f"{text_links}{preis_str}\n{zeile2}\n\n")
            drucker.write("-" * BON_WIDTH + "\n")
            drucker.write(f"GESAMT: {gesamt:.2f} EUR\n")
            drucker.write("=" * BON_WIDTH + "\nDanke für deinen Einkauf!\n" + "\n"*3 + "\x1D\x56\x00")
    except Exception as e:
        logger.error(f"Fehler beim Drucken: {e}")

class DisplayManager:
    def __init__(self, device: str, line_length: int = 20):
        self.display = vfd.BA63(device)
        self.line_length = line_length

    def clear(self) -> None:
        self.display.clear()

    def write(self, text: str, line: int, row: int = 1) -> None:
        self.display.write(text, line=line, row=row)

    def show_screensaver(self) -> None:
        """
        Aktualisiert das Display mit Datum und Uhrzeit und plant die nächste Aktualisierung nach 60 Sekunden.
        """
        self.clear()
        from time import strftime
        self.write("CASPARs Laden", line=1)
        self.write(strftime("%d.%m.%Y %H:%M"), line=2)
        asyncio.get_event_loop().call_later(60, self.show_screensaver)

class KassenScannerProtocol(asyncio.Protocol):
    def __init__(self, artikel_file: str, display_manager: DisplayManager, unknown_file: str = "unbekannte_barcodes.txt"):
        self.artikel_db = ArtikelDB(artikel_file)
        self.display = display_manager
        self.unknown_file = unknown_file
        self.warenkorb: List[Tuple[str, str, float]] = []
        self.unbekannte_barcodes: Set[str] = set()
        self._load_unknowns()

    def _load_unknowns(self) -> None:
        if os.path.exists(self.unknown_file):
            with open(self.unknown_file, "r", encoding="utf-8") as f:
                self.unbekannte_barcodes = {line.strip() for line in f if line.strip()}

    def connection_made(self, transport: asyncio.Transport) -> None:
        self.transport = transport
        logger.info("Scanner verbunden")
        try:
            transport.serial.rts = False
        except Exception:
            logger.warning("RTS konnte nicht gesetzt werden")

    def data_received(self, data: bytes) -> None:
        code = data.decode(errors="ignore").strip()
        logger.debug(f"Empfangen: {code}")
        if code == STEUERCODE_BEZAHLEN:
            asyncio.create_task(self.bezahlen())
        elif code == STEUERCODE_LOESCHEN:
            self.loeschen()
        else:
            self.artikel_hinzufuegen(code)

    def artikel_hinzufuegen(self, code: str) -> None:
        artikel = self.artikel_db.suche(code)
        if artikel:
            zeile1, zeile2, preis = artikel
            self.warenkorb.append((zeile1, zeile2, preis))
            logger.info(f"Hinzugefügt: {zeile1} | {zeile2} | {preis:.2f} EUR")
            self.display.clear()
            preis_str = f"{preis:.2f}".replace(".", ",") + " EUR"
            max_len = self.display.line_length - len(preis_str)
            text_links = zeile1[:max_len].ljust(max_len)
            self.display.write(text_links + preis_str, line=1)
            self.display.write(zeile2, line=2)
        else:
            if code not in self.unbekannte_barcodes:
                self.unbekannte_barcodes.add(code)
                self._append_unknown(code)
            logger.warning(f"Artikel nicht gefunden für Barcode: {code}")
            self.display.clear()
            self.display.write("Unbekannter Code", line=1)
            self.display.write(code, line=2)

    def _append_unknown(self, code: str) -> None:
        try:
            with tempfile.NamedTemporaryFile('w', delete=False, encoding='utf-8') as tmp:
                tmp.write(code + "\n")
                temp_name = tmp.name
            os.replace(temp_name, self.unknown_file)
        except Exception as e:
            logger.error(f"Fehler beim Schreiben unbekannter Barcodes: {e}")

    async def bezahlen(self) -> None:
        try:
            self.artikel_db.refresh()
        except Exception as e:
            logger.error(f"Fehler beim Aktualisieren der Artikel-Datenbank: {e}")
            self.display.clear()
            self.display.write("DB Fehler", line=1)
            return
        if not self.warenkorb:
            self.display.clear()
            self.display.write("Nichts zu zahlen", line=1)
            return
        gesamt = sum(preis for _, _, preis in self.warenkorb)
        self.display.clear()
        self.display.write("Summe:", line=1)
        self.display.write(f"{gesamt:.2f} EUR", line=2)
        logger.info("Drucke Bon")
        for ze1, ze2, pr in self.warenkorb:
            logger.info(f" {ze1} | {ze2} | {pr:.2f} EUR")
        logger.info(f" Gesamtbetrag: {gesamt:.2f} EUR")
        await asyncio.to_thread(drucke_bon, self.warenkorb, gesamt)
        self.warenkorb.clear()
        asyncio.get_event_loop().call_later(60, self.display.show_screensaver)

    def loeschen(self) -> None:
        self.warenkorb.clear()
        logger.info("Warenkorb gelöscht")
        self.display.clear()
        self.display.write("Warenkorb", line=1)
        self.display.write("gelöscht", line=2)

    def connection_lost(self, exc: Exception) -> None:
        logger.info("Scanner getrennt")
        asyncio.get_event_loop().stop()

# Hauptprogramm
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
    display_mgr = DisplayManager("/dev/ttySC0")
    protocol_factory = lambda: KassenScannerProtocol("artikel.csv", display_mgr)
    loop = asyncio.get_event_loop()
    display_mgr.show_screensaver()
    coro = serial_asyncio.create_serial_connection(loop, protocol_factory, SCANNER_DEVICE, baudrate=9600)
    transport, protocol = loop.run_until_complete(coro)
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        logger.info("Programm beendet")
    finally:
        loop.close()
