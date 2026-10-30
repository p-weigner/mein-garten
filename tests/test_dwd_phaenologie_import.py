"""DWD-Phänologie-Importtests ohne Netzwerk, Wetter oder Standortdaten."""
from datetime import date
import io
import json
import unittest

from tools.dwd_phaenologie_export import (
    INDICATORS, MIN_STATIONS, YEARS,
    SOURCE, LICENSE, aggregate, build_data, parse_rows, parse_stations,
    region_contains, select_observations,
)


def dwd_row(sid, year, obj, phase, when, julday=None, qb=1, qn=1):
    when = date.fromisoformat(when)
    # DWD-365-Tage-Skala im Schaltjahr ab März.
    if julday is None:
        julday = when.timetuple().tm_yday
        if when.year % 4 == 0 and when.month >= 3:
            julday -= 1
    return (
        f"{sid};{year};{qn};{obj};{phase};{when:%Y%m%d};{qb};{julday};eor;\n"
    )


def dwd_text(*rows):
    return (
        "Stations_id; Referenzjahr; Qualitaetsniveau; Objekt_id; Phase_id;"
        " Eintrittsdatum;Eintrittsdatum_QB; Jultag;eor;\n" +
        "".join(rows)
    ).encode("latin-1")


class TestDwdPhaenologieImport(unittest.TestCase):
    def setUp(self):
        self.stations = {
            str(i).zfill(5): {"latitude": 52.8, "longitude": 13.5}
            for i in range(1, 9)
        }
        self.stations["00009"] = {"latitude": 48.5, "longitude": 11.5}

    def test_dwd_formate_mit_leerzeichen_und_dokumentiertem_header(self):
        rows = list(parse_rows(dwd_text(
            dwd_row("00001", 2024, 109, 5, "2024-03-05", 64)
        )))
        self.assertEqual(rows[0]["Referenzjahr"], "2024")
        self.assertEqual(rows[0]["Jultag"], "64")
        self.assertEqual(rows[0]["Eintrittsdatum"], "20240305")

    def test_dwd_schaltjahr_365er_skalierung_ab_maerz(self):
        sample = dwd_text(
            dwd_row("00001", 2024, 109, 5, "2024-03-05", 64),
            dwd_row("00002", 2025, 109, 5, "2025-03-05", 64),
            dwd_row("00003", 2024, 109, 5, "2024-03-05", 65),
        )
        result, rejected = select_observations(sample, self.stations, 109, 5)
        self.assertEqual(result[2024]["00001"], date(2024, 3, 5))
        self.assertEqual(result[2025]["00002"], date(2025, 3, 5))
        self.assertNotIn("00003", result[2024])
        self.assertEqual(rejected.get("jultag_mismatch"), 1)

    def test_quality_flags_keine_zweifelhaften_werte(self):
        raw = dwd_text(
            dwd_row("00001", 2025, 113, 5, "2025-02-08", qb=1, qn=1),
            dwd_row("00002", 2025, 113, 5, "2025-02-08", qb=5),
            dwd_row("00003", 2025, 113, 5, "2025-02-08", qb=8),
            dwd_row("00004", 2025, 113, 5, "2025-02-08", qb=1, qn=7),
        )
        result, rejected = select_observations(raw, self.stations, 113, 5)
        self.assertEqual(set(result[2025]), {"00001", "00004"})
        self.assertEqual(rejected["quality"], 2)

    def test_widersprechende_stationsdaten_nicht_vorausgewaehlt(self):
        raw = dwd_text(
            dwd_row("00001", 2025, 109, 5, "2025-03-11"),
            dwd_row("00001", 2025, 109, 5, "2025-03-12"),
            dwd_row("00002", 2025, 109, 5, "2025-03-14"),
        )
        entries, rejected = select_observations(raw, self.stations, 109, 5)
        self.assertNotIn("00001", entries[2025])
        self.assertEqual(entries[2025]["00002"], date(2025, 3, 14))
        self.assertEqual(rejected["station_date_conflict"], 1)

    def test_grosses_gebiet_ist_keine_heimadresse(self):
        northeast = {
            "lat_min": 52.0, "lat_max": 54.2, "lon_min": 12.0, "lon_max": 15.0,
        }
        self.assertTrue(region_contains(northeast, self.stations["00001"]))
        self.assertFalse(region_contains(northeast, self.stations["00009"]))
        self.assertTrue(region_contains(
            {"label": "Deutschland"}, self.stations["00009"]
        ))

    def test_weniger_als_fuenf_stationen_kein_angeblicher_regionalmedian(self):
        self.assertIsNone(aggregate([date(2025, 2, 1)] * (MIN_STATIONS - 1)))
        stat = aggregate([
            date(2025, 2, 1), date(2025, 2, 3), date(2025, 2, 4),
            date(2025, 2, 6), date(2025, 2, 10),
        ])
        self.assertEqual(stat["stationen"], 5)
        self.assertEqual(stat["median"], "2025-02-04")
        self.assertEqual(stat["quartil_von"], "2025-02-03")
        self.assertEqual(stat["quartil_bis"], "2025-02-06")

    def test_eindeutige_beschriftete_region_und_alle_quellen(self):
        keys = {item[0] for item in INDICATORS}
        samples = {
            key: {2025: {
                str(sid).zfill(5): date(2025, 3, 12 + sid)
                for sid in range(1, 7)
            }}
            for key in keys
        }
        packet = build_data(samples, self.stations, "2026-10-30")
        self.assertEqual(packet["quelle"], SOURCE)
        self.assertEqual(packet["lizenz"], LICENSE)
        self.assertEqual(len(packet["werte"]), 6)
        self.assertEqual(set(x["region"] for x in packet["werte"]),
                         {"nordost", "deutschland"})
        self.assertTrue(all(x["stationen"] == 6 for x in packet["werte"]))
        self.assertEqual(packet["abgerufen_am"], "2026-10-30")
        self.assertIn("keine", packet["hinweis"].lower())

    def test_headerwechsel_statt_falschen_kennzahlen_blockiert(self):
        with self.assertRaisesRegex(ValueError, "Datenschema"):
            list(parse_rows(b"some;other;header\n1;2;3\n"))


if __name__ == "__main__":
    unittest.main()
