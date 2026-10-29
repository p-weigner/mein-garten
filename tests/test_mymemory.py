import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.anbieter import AnbieterFehler, KontingentErschoepft
from tools.mymemory import (
    MAX_REQUEST_BYTES, Tagesbudget, MyMemoryUebersetzer, segmente,
)


class FakeResponse:
    status = 200

    def __init__(self, data):
        self.contents = json.dumps(data).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, length):
        return self.contents[:length]


def response(text):
    return FakeResponse({"responseStatus": 200, "responseData": {"translatedText": text}})


class TestSegmentierung(unittest.TestCase):
    def test_normaler_satz(self):
        self.assertEqual(segmente("Water regularly."), ["Water regularly."])

    def test_zwei_absaetze_werden_getrennt(self):
        self.assertEqual(segmente("Water regularly.\n\nAvoid waterlogging."),
                         ["Water regularly.", "Avoid waterlogging."])

    def test_500_bytes_grenze_bei_umlauten(self):
        pieces = segmente("Für " + "feucht " * 88 + "halten.")
        self.assertTrue(pieces)
        self.assertTrue(all(len(p.encode("utf-8")) <= MAX_REQUEST_BYTES for p in pieces))

    def test_zu_langes_wort_abgelehnt(self):
        with self.assertRaises(ValueError):
            segmente("x" * 501)

    def test_kein_leertext(self):
        with self.assertRaises(ValueError):
            segmente(" \n ")

    def test_zu_langer_gesamttext(self):
        with self.assertRaises(ValueError):
            segmente("abc " * 3100)

    def test_satzende_ist_schnittgrenze(self):
        self.assertEqual(segmente("Keep moist. Do not waterlog."),
                         ["Keep moist.", "Do not waterlog."])

    def test_kurzere_texte_werden_nicht_stueckweise_zerhackt(self):
        sentence = "Do not prune in autumn, because new flower buds have already formed."
        self.assertEqual(segmente(sentence), [sentence])


class TestTagesbudget(unittest.TestCase):
    def test_tagesbudget_persistiert(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "budget.json"
            Tagesbudget(path, limit=17).reservieren("123456789")
            with self.assertRaises(KontingentErschoepft):
                Tagesbudget(path, limit=17).reservieren("123456789")
            self.assertTrue(path.exists())

    def test_nicht_mehr_als_5000_einrichten(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                Tagesbudget(Path(d) / "b.json", limit=5001)

    def test_budgetsperre_vor_http(self):
        with tempfile.TemporaryDirectory() as d:
            budget = Tagesbudget(Path(d) / "b.json", limit=5)
            with patch("tools.mymemory.urllib.request.urlopen") as net:
                with self.assertRaises(KontingentErschoepft):
                    MyMemoryUebersetzer(budget)("123456789")
                net.assert_not_called()

    def test_keine_kostenpflichtigen_fallbacks(self):
        with tempfile.TemporaryDirectory() as d:
            budget = Tagesbudget(Path(d) / "b.json", limit=5000)
            self.assertEqual(budget.limit, 5000)


class TestMyMemory(unittest.TestCase):
    def test_anonym_echt_nur_get_en_de(self):
        with tempfile.TemporaryDirectory() as d:
            budget = Tagesbudget(Path(d) / "budget.json")
            with patch("tools.mymemory.urllib.request.urlopen", return_value=response(
                "Die Pflanze benötigt Halbschatten.")) as net:
                text = MyMemoryUebersetzer(budget)(
                    "The plant prefers partial shade.")
                self.assertEqual(text, "Die Pflanze benötigt Halbschatten.")
                req = net.call_args.args[0]
                self.assertTrue(req.full_url.startswith("https://api.mymemory.translated.net/get?"))
                self.assertIn("langpair=en%7Cde", req.full_url)
                self.assertNotIn("de=", req.full_url)
                self.assertEqual(req.get_method(), "GET")

    def test_unerwartete_antwort_abgelehnt(self):
        with tempfile.TemporaryDirectory() as d:
            with patch("tools.mymemory.urllib.request.urlopen", return_value=FakeResponse(
                {"responseStatus": 429, "responseData": {"translatedText": "Limit"}})):
                with self.assertRaises(AnbieterFehler):
                    MyMemoryUebersetzer(Tagesbudget(Path(d) / "budget.json"))("Water.")

    def test_keine_html_antworten(self):
        with tempfile.TemporaryDirectory() as d:
            with patch("tools.mymemory.urllib.request.urlopen", return_value=response(
                "<script>alert('x')</script>")):
                with self.assertRaises(AnbieterFehler):
                    MyMemoryUebersetzer(Tagesbudget(Path(d) / "budget.json"))("Water.")

    def test_html_entitaeten_sicher_entschluesseln(self):
        with tempfile.TemporaryDirectory() as d:
            with patch("tools.mymemory.urllib.request.urlopen", return_value=response(
                "Wasser &amp; Licht")):
                text = MyMemoryUebersetzer(Tagesbudget(Path(d) / "budget.json"))("Water and light.")
                self.assertEqual(text, "Wasser & Licht")

    def test_gesplitteter_text_mehrere_requests(self):
        with tempfile.TemporaryDirectory() as d:
            with patch("tools.mymemory.urllib.request.urlopen",
                       side_effect=[response("Gießen."), response("Schatten.")]) as net:
                text = MyMemoryUebersetzer(Tagesbudget(Path(d) / "budget.json"))(
                    "Water.\n\nShade.")
                self.assertEqual(text, "Gießen. Schatten.")
                self.assertEqual(net.call_count, 2)

    def test_abweichende_antwort_kein_erfolg(self):
        with tempfile.TemporaryDirectory() as d:
            with patch("tools.mymemory.urllib.request.urlopen",
                       return_value=FakeResponse({"responseStatus": 200, "responseData": {}})):
                with self.assertRaises(AnbieterFehler):
                    MyMemoryUebersetzer(Tagesbudget(Path(d) / "budget.json"))("Water.")


if __name__ == "__main__":
    unittest.main()
