"""Isolierte Tests einer sicheren, optionalen europäischen Forschungsquelle."""
from __future__ import annotations

import io
import unittest
from unittest.mock import patch

from tools.eive_europa_quellenprobe import (
    EXPECTED_MD5, RECORD, REQUIRED_LICENSE, bounded_download,
    lizenz_id, limited_value, workbook_preview,
)


class TestEiveEuropaQuellenprobe(unittest.TestCase):
    def test_eindeutige_lizenz_nur_im_korrekten_record(self):
        self.assertEqual(lizenz_id({
            "id": int(RECORD),
            "metadata": {"license": {"id": REQUIRED_LICENSE}},
        }), REQUIRED_LICENSE)
        with self.assertRaisesRegex(ValueError, "Datensatz-ID"):
            lizenz_id({
                "id": 42, "metadata": {"license": {"id": REQUIRED_LICENSE}},
            })

    def test_offene_publikation_allein_ist_kein_datensatz_lizenzbeleg(self):
        with self.assertRaisesRegex(ValueError, "Lizenz"):
            lizenz_id({"id": int(RECORD), "metadata": {}})
        with self.assertRaisesRegex(ValueError, "CC BY"):
            lizenz_id({
                "id": int(RECORD), "metadata": {"license": {"id": "cc-by-nc-4.0"}},
            })
        with self.assertRaises(ValueError):
            lizenz_id({
                "id": int(RECORD),
                "metadata": {"rights": [{"id": "cc-by-4.0"},
                                       {"id": "all-rights-reserved"}]},
            })

    def test_zenodo_adressen_strikt_begrenzt(self):
        with self.assertRaisesRegex(ValueError, "Zenodo"):
            bounded_download("https://attacker.example/any", 100)
        with self.assertRaisesRegex(ValueError, "Zenodo"):
            bounded_download("http://zenodo.org/something", 100)

    def test_bis_zur_grenze_lesen_und_uebergrosse_antwort_abweisen(self):
        class DummyResponse:
            def __init__(self, data):
                self._content = io.BytesIO(data)
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def read(self, count):
                return self._content.read(count)
        with patch("urllib.request.urlopen", return_value=DummyResponse(b"abcd")):
            self.assertEqual(
                bounded_download("https://zenodo.org/safe", 4), b"abcd"
            )
        with patch("urllib.request.urlopen", return_value=DummyResponse(b"abcde")):
            with self.assertRaisesRegex(ValueError, "Größenlimit"):
                bounded_download("https://zenodo.org/safe", 4)

    def test_xlsx_vorschau_lokal_ohne_formeln_oder_volle_zeilen(self):
        from openpyxl import Workbook
        book = Workbook()
        sheet = book.active
        sheet.title = "Nischenwerte"
        sheet.append(["Taxon", "M", "N", "R", "L", "T", "Quellensystem"])
        sheet.append(["Rosa canina", 4.5, 3.4, 5, 6.0, 6.3, "Forschungswert"])
        sheet.append(["Papier", "=1+2", None])
        outfile = io.BytesIO()
        book.save(outfile)
        result = workbook_preview(outfile.getvalue())
        self.assertEqual(result[0]["blatt"], "Nischenwerte")
        self.assertEqual(result[0]["anfang"][0][:3], ["Taxon", "M", "N"])
        self.assertEqual(result[0]["anfang"][1][0], "Rosa canina")
        self.assertIsNone(result[0]["anfang"][2][1])

    def test_eingaben_sind_begrenzt(self):
        self.assertEqual(limited_value("A" * 120), "A" * 90)
        self.assertIsNone(limited_value(""))
        self.assertIsNone(limited_value({"token": "secret"}))
        self.assertEqual(limited_value(12.3), 12.3)
        self.assertEqual(len(EXPECTED_MD5), 32)


if __name__ == "__main__":
    unittest.main()
