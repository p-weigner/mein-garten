"""Exploration der DWD-Phänologie-Quelldaten, nur in GitHub CI.

Lädt ausschließlich fest benannte amtliche Dateien. Gibt kurze Metadaten/
Spaltennamen aus; keine Gartenbenutzerdaten, keine Ortsdaten werden übertragen.
"""
from __future__ import annotations

import csv
import io
import json
import urllib.request

BASE = (
    "https://opendata.dwd.de/climate_environment/CDC/"
    "observations_germany/phenology/immediate_reporters/wild/recent/"
)
FILES = (
    "PH_Sofortmelder_Wildwachsende_Pflanze_Hasel_akt.txt",
    "PH_Sofortmelder_Wildwachsende_Pflanze_Forsythie_akt.txt",
    "PH_Sofortmelder_Wildwachsende_Pflanze_Rotbuche_akt.txt",
)
STATIONS = (
    "https://opendata.dwd.de/climate_environment/CDC/help/"
    "PH_Beschreibung_Phaenologie_Stationen_Sofortmelder.txt"
)
MAX_BYTES = 2_000_000


def download(url: str) -> bytes:
    request = urllib.request.Request(
        url, headers={"User-Agent": "MeinGarten-DWD-Phenology-Source-Audit/1.0"}
    )
    with urllib.request.urlopen(request, timeout=45) as stream:
        data = stream.read(MAX_BYTES + 1)
    if not data or len(data) > MAX_BYTES:
        raise ValueError("Datei leer oder zu groß: " + url)
    return data


def sample(name: str, raw: bytes) -> None:
    # Latin-1 ist verlustfrei für Spaltentrenner und IDs,
    # ohne voreilige Annahme zur tatsächlichen Textkodierung.
    lines = raw.decode("latin-1").splitlines()
    print("DWD_META", json.dumps({
        "datei": name, "groesse": len(raw), "zeilen": len(lines),
        "erste_zeilen": [line[:250] for line in lines[:4]],
        "semikolon_spalten": [
            len(x.split(";")) for x in lines[:4]
        ],
    }, ensure_ascii=True), flush=True)
    if lines and name != "stations":
        for delimiter in (";", ",", "\t"):
            reader = csv.DictReader(io.StringIO("\n".join(lines[:5])), delimiter=delimiter)
            if reader.fieldnames and len(reader.fieldnames) > 3:
                print("DWD_HEADER", json.dumps({
                    "datei": name, "delimiter": repr(delimiter),
                    "fields": reader.fieldnames,
                    "row": next(reader, {}),
                }, ensure_ascii=True), flush=True)


def main() -> None:
    for name in FILES:
        sample(name, download(BASE + name))
    sample("stations", download(STATIONS))


if __name__ == "__main__":
    main()
