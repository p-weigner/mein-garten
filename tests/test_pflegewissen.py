import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.pflegewissen import (
    Pflegehinweis, ArtNichtPassend, gleiche_art, artnorm,
    normalisiere_openplantbook, normalisiere_permapeople,
    LokalerUebersetzungscache, uebersetze_hinweise, fuer_deutsche_anzeige,
)
from tools.anbieter import (
    permapeople_suche, Monatsbudget, AzureUebersetzer,
    KontingentErschoepft, AnbieterFehler,
)


class FakeResponse:
    status = 200
    def __init__(self, result):
        self.contents = json.dumps(result).encode("utf-8")
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self, _limit): return self.contents


def hint(text="Water regularly", field="watering"):
    return Pflegehinweis(
        art="Hydrangea macrophylla", feld=field, original=text, sprache_original="en",
        quelle="OpenPlantbook", quell_id="hydrangea macrophylla",
        quell_url="https://open.plantbook.io", lizenz_hinweis="Nutzung prüfen",
        abgerufen_utc="2026-10-29T00:00:00Z",
    )


class TestArtenUndQuellen(unittest.TestCase):
    def test_name_genau(self):
        self.assertTrue(gleiche_art("Hydrangea macrophylla", "hydrangea MACROPHYLLA"))
    def test_hybridzeichen(self):
        self.assertTrue(gleiche_art("Citrus × limon", "Citrus x limon"))
    def test_andere_art_abgelehnt(self):
        self.assertFalse(gleiche_art("Hydrangea macrophylla", "Hydrangea paniculata"))
    def test_gattung_abgelehnt(self):
        self.assertFalse(gleiche_art("Hydrangea macrophylla", "Hydrangea"))
    def test_leerer_name_abgelehnt(self):
        self.assertFalse(gleiche_art("", ""))
    def test_opb_mit_passendem_pid(self):
        data={"pid":"hydrangea macrophylla","watering":"Moist soil",
              "sunlight":"Partial shade","pruning":"Avoid severe cuts"}
        entries=normalisiere_openplantbook(data,"Hydrangea macrophylla")
        self.assertEqual({x.feld for x in entries},{"watering","sunlight","pruning"})
        self.assertTrue(all(x.aufgabenfreigabe is False for x in entries))
    def test_opb_mit_falschem_pid(self):
        with self.assertRaises(ArtNichtPassend):
            normalisiere_openplantbook({"pid":"hydrangea paniculata","pruning":"Cut hard"},"Hydrangea macrophylla")
    def test_opb_ohne_identitaet(self):
        with self.assertRaises(ArtNichtPassend):
            normalisiere_openplantbook({"watering":"Often"},"Hydrangea macrophylla")
    def test_opb_mit_ungueltigen_feldern(self):
        entries=normalisiere_openplantbook(
            {"pid":"hydrangea macrophylla","watering":False,"soil":"","sunlight":None},"Hydrangea macrophylla")
        self.assertEqual(entries,[])
    def test_permapeople_nur_verifizierte_attribute(self):
        data={"id":123,"scientific_name":"Hydrangea macrophylla",
              "link":"/plants/hydrangea-macrophylla",
              "data":[{"key":"Water requirement","value":"Moist"},
                      {"key":"Light requirement","value":"Partial shade"},
                      {"key":"Edible","value":"true"},
                      {"key":"Toxic","value":"false"},
                      {"key":"Soil type","value":"Loamy"}]}
        entries=normalisiere_permapeople(data,"Hydrangea macrophylla")
        self.assertEqual({x.feld for x in entries},{"watering","sunlight","soil"})
        self.assertTrue(all("permapeople.org" in x.quell_url for x in entries))
        self.assertTrue(all("CC BY-SA" in x.lizenz_hinweis for x in entries))
    def test_permapeople_falsche_art(self):
        with self.assertRaises(ArtNichtPassend):
            normalisiere_permapeople(
                {"scientific_name":"Hydrangea paniculata","data":[]},"Hydrangea macrophylla")
    def test_permapeople_unerwartete_datenform(self):
        with self.assertRaises(ValueError):
            normalisiere_permapeople(
                {"scientific_name":"Hydrangea macrophylla","data":{}},
                "Hydrangea macrophylla",
            )
    def test_quelltext_pruefsumme(self):
        h=hint()
        self.assertEqual(len(h.original_sha256),64)
        self.assertFalse(h.aufgabenfreigabe)
    def test_ueberlanger_text_abgelehnt(self):
        with self.assertRaises(ValueError):
            normalisiere_openplantbook(
                {"pid":"hydrangea macrophylla","pruning":"a"*12001},
                "Hydrangea macrophylla",
            )


class TestDeutscheAnzeige(unittest.TestCase):
    def test_ohne_dienst_keine_englische_anzeige(self):
        with tempfile.TemporaryDirectory() as d:
            items=uebersetze_hinweise([hint()],None,LokalerUebersetzungscache(Path(d)/"cache.json"))
        ansicht=fuer_deutsche_anzeige(items)[0]
        self.assertIsNone(ansicht["text_de"])
        self.assertFalse(ansicht["deutsch_verfuegbar"])
    def test_uebersetzung_einmalig(self):
        with tempfile.TemporaryDirectory() as d:
            cache=LokalerUebersetzungscache(Path(d)/"cache.json")
            count=[]
            def translator(text):
                count.append(text)
                return "Regelmäßig gießen"
            one=uebersetze_hinweise([hint()],translator,cache)
            two=uebersetze_hinweise([hint()],translator,cache)
            self.assertEqual(count,["Water regularly"])
            self.assertEqual(one[0].deutsch,"Regelmäßig gießen")
            self.assertEqual(two[0].uebersetzung,"cache")
            self.assertFalse(fuer_deutsche_anzeige(one)[0]["automatische_aufgabe_erlaubt"])
            self.assertEqual(LokalerUebersetzungscache(Path(d)/"cache.json").daten, cache.daten)
    def test_cache_berechtigungen(self):
        if os.name != "posix":
            self.skipTest("POSIX-only")
        with tempfile.TemporaryDirectory() as d:
            cache=LokalerUebersetzungscache(Path(d)/"cache.json")
            cache.put("a","b")
            self.assertEqual((Path(d)/"cache.json").stat().st_mode & 0o777, 0o600)
    def test_cache_fuer_andere_quelle_nicht_wiederverwenden(self):
        k=LokalerUebersetzungscache.schluessel
        self.assertNotEqual(k("Water","OpenPlantbook","watering"),
                            k("Water","Permapeople","watering"))
    def test_original_bleibt_unveraendert(self):
        with tempfile.TemporaryDirectory() as d:
            value=hint()
            uebersetze_hinweise([value],lambda x:"Feucht halten",
                                LokalerUebersetzungscache(Path(d)/"c.json"))
            self.assertEqual(value.original,"Water regularly")
            self.assertEqual(value.uebersetzung,"automatisch")
    def test_uebersetzungsfehler_faellt_sicher_zurueck(self):
        with tempfile.TemporaryDirectory() as d:
            def fail(_): raise RuntimeError("Übersetzungsdienst offline")
            item=uebersetze_hinweise([hint()],fail,LokalerUebersetzungscache(Path(d)/"c.json"))[0]
            self.assertIsNone(item.deutsch)
            self.assertEqual(item.uebersetzung,"fehler")


class TestAPIs(unittest.TestCase):
    def test_permapeople_suche_nur_exakte_art(self):
        data={"plants":[{"scientific_name":"Hydrangea macrophylla","data":[]},
                         {"scientific_name":"Hydrangea paniculata","data":[]}]}
        with patch("tools.anbieter.urllib.request.urlopen",return_value=FakeResponse(data)) as fn:
            result=permapeople_suche("Hydrangea macrophylla","testid","testsecret")
            self.assertEqual(len(result),1)
            req=fn.call_args.args[0]
            self.assertEqual(req.get_header("X-permapeople-key-id"),"testid")
            self.assertEqual(req.get_header("X-permapeople-key-secret"),"testsecret")
    def test_permapeople_kein_schluessel(self):
        with self.assertRaises(ValueError):
            permapeople_suche("Hydrangea macrophylla","","")
    def test_permapeople_ungueltige_antwort(self):
        with patch("tools.anbieter.urllib.request.urlopen",return_value=FakeResponse({"xx":[]})):
            with self.assertRaises(AnbieterFehler):
                permapeople_suche("Hydrangea macrophylla","id","secret")
    def test_budget_stoppt_vor_cloudaufruf(self):
        with tempfile.TemporaryDirectory() as d:
            budget=Monatsbudget(Path(d)/"limit.json",limit=10)
            budget.reservieren("123456789")
            with self.assertRaises(KontingentErschoepft):
                budget.reservieren("abc")
            with self.assertRaises(KontingentErschoepft):
                budget.reservieren("12345678901")
    def test_budget_dauerhaft(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"limit.json"
            Monatsbudget(path,limit=8).reservieren("12345")
            with self.assertRaises(KontingentErschoepft):
                Monatsbudget(path,limit=8).reservieren("1234")
    def test_azure_antwort_und_sicherheitsbudget(self):
        with tempfile.TemporaryDirectory() as d:
            budget=Monatsbudget(Path(d)/"limit.json",limit=50)
            resp=[{"translations":[{"text":"Halbschatten"}]}]
            with patch("tools.anbieter.urllib.request.urlopen",return_value=FakeResponse(resp)) as fn:
                value=AzureUebersetzer("TEST_KEY","westeurope",budget)("Partial shade")
                self.assertEqual(value,"Halbschatten")
                req=fn.call_args.args[0]
                self.assertEqual(req.get_header("Ocp-apim-subscription-key"),"TEST_KEY")
                self.assertEqual(req.get_header("Ocp-apim-subscription-region"),"westeurope")
                self.assertEqual(req.method,"POST")
    def test_azure_schluessel_erforderlich(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                AzureUebersetzer("", "", Monatsbudget(Path(d)/"b.json"))
    def test_kein_ungepruefter_pflegekalender(self):
        items=[hint("Cut back hard","pruning"),hint("Fertilize generously","fertilization")]
        self.assertTrue(all(not x.aufgabenfreigabe for x in items))
        self.assertTrue(all(not x["automatische_aufgabe_erlaubt"] for x in fuer_deutsche_anzeige(items)))


if __name__=="__main__":
    unittest.main()
