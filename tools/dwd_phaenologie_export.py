"""Kompakte DWD-Phänologie-Referenzdaten für einen schreibgeschützten Vergleich.

NUR DEVELOPMENT/CI: Offizielle DWD-Dateien werden in GitHub Actions geladen,
NICHT während des Betriebs von Home Assistant Green. Keine Benutzerstandorte,
Gartennotizen oder individuellen Beobachtungen werden an den DWD übertragen.

Dies sind gemeldete DWD-Beobachtungen aus einem großen geografischen Rechteck,
KEINE prognostizierten Phasentermine, Pflege- oder Gartenempfehlungen.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import csv
from datetime import date, datetime, timezone
import hashlib
import io
import json
from pathlib import Path
from statistics import median_low
from tools.dwd_phaenologie_probe import download, BASE, STATIONS
from tools.openplantdb_umfang_probe import ROOT

SOURCE = "Deutscher Wetterdienst (DWD), Climate Data Center"
LICENSE = "CC BY 4.0"
SOURCE_PAGE = (
    "https://opendata.dwd.de/climate_environment/CDC/"
    "observations_germany/phenology/immediate_reporters/wild/recent/"
)
REGIONS = {
    "nordost": {
        "label": "Nordostdeutsches Referenzgebiet (grob, 52,0–54,2° N / 12–15° O)",
        "lat_min": 52.0,
        "lat_max": 54.2,
        "lon_min": 12.0,
        "lon_max": 15.0,
    },
    "deutschland": {
        "label": "Deutschlandweite DWD-Beobachtungsstationen",
    },
}
INDICATORS = (
    ("hasel_bluete", "Hasel (Arten nicht unterschieden)", "Blütebeginn",
     "PH_Sofortmelder_Wildwachsende_Pflanze_Hasel_akt.txt", 113, 5),
    ("forsythie_bluete", "Forsythie", "Blütebeginn",
     "PH_Sofortmelder_Wildwachsende_Pflanze_Forsythie_akt.txt", 109, 5),
    ("rotbuche_blatt", "Rotbuche", "Blattentfaltung",
     "PH_Sofortmelder_Wildwachsende_Pflanze_Rotbuche_akt.txt", 123, 4),
)
YEARS = (2023, 2024, 2025, 2026)
MIN_STATIONS = 5
OUT = ROOT / "custom_components" / "mein_garten" / "data" / "dwd_phaenologie_region_v1.json"


def parse_rows(raw: bytes):
    # Die offiziellen Textdateien besitzen Semikolon-Trenner und können
    # lateinische Windows-Zeichen enthalten: Latin-1 ist verlustfrei für IDs.
    reader = csv.DictReader(io.StringIO(raw.decode("latin-1")), delimiter=";")
    names = {field.strip() for field in (reader.fieldnames or []) if field}
    required = {
        "Stations_id", "Referenzjahr", "Qualitaetsniveau", "Objekt_id",
        "Phase_id", "Eintrittsdatum", "Eintrittsdatum_QB", "Jultag",
    }
    if not required.issubset(names):
        raise ValueError("DWD-Datenschema verändert, Import abgebrochen")
    for rawrow in reader:
        yield {
            str(k).strip(): str(v).strip()
            for k, v in rawrow.items() if k is not None and v is not None
        }


def parse_stations(raw: bytes) -> dict[str, dict]:
    reader = csv.DictReader(io.StringIO(raw.decode("latin-1")), delimiter=";")
    required = {"Stations_id", "geograph.Breite", "geograph.Laenge"}
    names = {key.strip() for key in (reader.fieldnames or []) if key}
    if not required.issubset(names):
        raise ValueError("DWD-Stationsschema verändert, Import abgebrochen")
    stations = {}
    for entry in reader:
        row = {str(k).strip(): str(v).strip() for k, v in entry.items()
               if k is not None and v is not None}
        try:
            id_ = str(int(row["Stations_id"])).zfill(5)
            lat = float(row["geograph.Breite"].replace(",", "."))
            lon = float(row["geograph.Laenge"].replace(",", "."))
            if not (47.1 <= lat <= 55.2 and 5.0 <= lon <= 16.0):
                continue
            value = {"latitude": lat, "longitude": lon}
            if id_ in stations and stations[id_] != value:
                raise ValueError("DWD-Station mehrfach mit verschiedenen Koordinaten")
            stations[id_] = value
        except (ValueError, KeyError) as exc:
            # Nicht numerische Stationseinträge sind Metadaten, deren Spalten
            # nicht stillschweigend erraten werden dürfen.
            if isinstance(exc, ValueError) and "mehrfach" in str(exc):
                raise
    if len(stations) < 100:
        raise ValueError("Zu wenig gültige DWD-Stations-Metadaten")
    return stations


def select_observations(raw: bytes, stations: dict, object_id: int,
                        phase_id: int) -> tuple[dict, dict]:
    groups = defaultdict(lambda: defaultdict(list))
    rejected = Counter()
    for row in parse_rows(raw):
        try:
            year = int(row["Referenzjahr"])
            obj = int(row["Objekt_id"])
            phase = int(row["Phase_id"])
            if obj != object_id or phase != phase_id or year not in YEARS:
                continue
            qb = int(row["Eintrittsdatum_QB"])
            qn = int(row["Qualitaetsniveau"])
            if qb != 1 or qn not in (1, 7, 10):
                rejected["quality"] += 1
                continue
            date_raw = row["Eintrittsdatum"]
            when = datetime.strptime(date_raw, "%Y%m%d").date()
            if when.year != year:
                rejected["year_mismatch"] += 1
                continue
            doy = (when - date(year, 1, 1)).days + 1
            if doy != int(row["Jultag"]):
                rejected["jultag_mismatch"] += 1
                continue
            id_ = str(int(row["Stations_id"])).zfill(5)
            station = stations.get(id_)
            if not station:
                rejected["station_unknown"] += 1
                continue
            groups[year][id_].append(when)
        except (KeyError, ValueError, OverflowError):
            rejected["row_invalid"] += 1

    # Der Phasenbeginn kann an einer Station mehrfach vorkommen (neue
    # Meldung, Korrektur); widersprüchliche Datumsangaben NICHT auswählen.
    unique = {}
    for year, entries in groups.items():
        unique[year] = {}
        for sid, dates in entries.items():
            if len(set(dates)) != 1:
                rejected["station_date_conflict"] += 1
                continue
            unique[year][sid] = dates[0]
    return unique, dict(rejected)


def region_contains(region: dict, station: dict) -> bool:
    if "lat_min" not in region:
        return True
    return (
        region["lat_min"] <= station["latitude"] <= region["lat_max"]
        and region["lon_min"] <= station["longitude"] <= region["lon_max"]
    )


def aggregate(values: list[date]) -> dict | None:
    """Q1/Median/Q3 als tatsächlich beobachtete Tage (kein Mittelwert erfunden)."""
    if len(values) < MIN_STATIONS:
        return None
    sorted_values = sorted(values)
    n = len(sorted_values)
    mid = median_low(sorted_values)
    q1 = sorted_values[(n - 1) // 4]
    q3 = sorted_values[3 * (n - 1) // 4]
    return {
        "stationen": n,
        "median": mid.isoformat(),
        "quartil_von": q1.isoformat(),
        "quartil_bis": q3.isoformat(),
    }


def build_data(data_by_indicator: dict, stations: dict, imported: str) -> dict:
    if not isinstance(imported, str) or len(imported) != 10:
        raise ValueError("Ungültiges Importsnapshot-Datum")
    results = []
    for key, name, stage, filename, obj, phase in INDICATORS:
        values = data_by_indicator.get(key)
        if values is None:
            raise ValueError("Pflichtindikator fehlt: " + key)
        for year in YEARS:
            for region_key, region in REGIONS.items():
                observed = [
                    when for sid, when in values.get(year, {}).items()
                    if sid in stations and region_contains(region, stations[sid])
                ]
                stats = aggregate(observed)
                if stats is None:
                    continue
                results.append({
                    "indikator": key,
                    "pflanze": name,
                    "phase": stage,
                    "region": region_key,
                    "jahr": year,
                    **stats,
                })
    if len(results) < 5:
        raise ValueError("Zu wenige ausreichend belegte DWD-Vergleichswerte")
    source_files = [
        {"datei": filename, "objekt_id": obj, "phase_id": phase}
        for _, _, _, filename, obj, phase in INDICATORS
    ]
    return {
        "schema": 1,
        "quelle": SOURCE,
        "lizenz": LICENSE,
        "quellen_url": SOURCE_PAGE,
        "abgerufen_am": imported,
        "meldeverfahren": "DWD Sofortmelder, wildwachsende Pflanzen",
        "qualitaetsfilter": "Eintrittsdatum_QB=1 (nicht beanstandet); QN=1,7,10",
        "hinweis": (
            "Gemeldete DWD-Stationsbeobachtungen, teils nur formal geprüft. "
            "Geografische Gebietsauswahl keine lokale Gartenmessung. "
            "Keine Prognose und keine Schnitt-, Dünge- oder Aussaatempfehlung."
        ),
        "regionen": REGIONS,
        "basis_stationsliste": STATIONS,
        "quell_dateien": source_files,
        "werte": results,
    }


def create_snapshot():
    station_raw = download(STATIONS)
    stations = parse_stations(station_raw)
    checksums = {"stationen": hashlib.sha256(station_raw).hexdigest()}
    measurements = {}
    diagnostics = {}
    for key, name, stage, filename, obj, phase in INDICATORS:
        raw = download(BASE + filename)
        checksums[key] = hashlib.sha256(raw).hexdigest()
        measurements[key], diagnostics[key] = select_observations(
            raw, stations, obj, phase
        )
    today = date.today().isoformat()
    data = build_data(measurements, stations, today)
    data["quell_sha256"] = checksums
    return data, diagnostics


def main():
    data, diag = create_snapshot()
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    if len(text.encode("utf-8")) > 55_000:
        raise ValueError("DWD-Snapshot ist nicht mehr kompakt")
    OUT.write_text(text, encoding="utf-8")
    print("DWD_SUMMARY", json.dumps({
        "abgerufen_am": data["abgerufen_am"],
        "stationen_gesamt": len(parse_stations(download(STATIONS))),
        "werte": len(data["werte"]),
        "region_kombinationen": dict(Counter(v["region"] for v in data["werte"])),
        "indicator_jahre": sorted({(v["indikator"], v["jahr"]) for v in data["werte"]}),
        "beispiele": [r for r in data["werte"]
                      if r["region"] == "nordost" and r["jahr"] == 2025],
        "verworfen": diag,
        "snapshot_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
    }, ensure_ascii=True), flush=True)
    # Nur auditierten, sehr kleinen Offline-Snapshot für GitHub-Connector
    # in feste Stücke aufteilen, keine Repository-Schreibrechte im CI.
    parts = [text[i:i + 1700] for i in range(0, len(text), 1700)]
    for i, fragment in enumerate(parts):
        print(f"DWD_PART|{i}|{len(parts)}|{json.dumps(fragment, ensure_ascii=True)}",
              flush=True)


if __name__ == "__main__":
    main()
