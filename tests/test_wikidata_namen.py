import unittest
from unittest.mock import patch

from tools.wikidata_namen import _taxon_name, suchname_de


class TestWikidataAliasSuche(unittest.TestCase):
    def test_nur_ein_taxon_p225(self):
        result=_taxon_name({"claims":{"P225":[{
            "mainsnak":{"datavalue":{"value":"Hydrangea macrophylla"}}
        }]}})
        self.assertEqual(result,"Hydrangea macrophylla")

    def test_falscher_gegenstand_kein_taxon(self):
        self.assertIsNone(_taxon_name({"claims":{"P31":[]}}))

    def test_suche_ueber_alias(self):
        search={"search":[
            {"id":"Q123","label":"Gartenhortensie",
             "match":{"type":"alias","text":"Bauernhortensie"}},
            {"id":"Q99","label":"Hortensie-Straße",
             "match":{"type":"label","text":"Hortensie-Straße"}},
        ]}
        details={"entities":{
            "Q123":{"claims":{"P225":[{
                "mainsnak":{"datavalue":{"value":"Hydrangea macrophylla"}}
            }]}},
            "Q99":{"claims":{"P31":[]}},
        }}
        with patch("tools.wikidata_namen._get",side_effect=[search,details]) as fn:
            candidates=suchname_de("Bauernhortensie")
        self.assertEqual(len(candidates),1)
        self.assertEqual(candidates[0]["wissenschaftlich"],"Hydrangea macrophylla")
        self.assertEqual(candidates[0]["wikidata_id"],"Q123")
        self.assertEqual(candidates[0]["alias"],"Bauernhortensie")
        self.assertEqual(candidates[0]["status"],"taxonomischer_vorschlag_nicht_verifiziert")
        self.assertEqual(fn.call_count,2)

    def test_leere_antwort_verursacht_keine_beliebige_zuordnung(self):
        with patch("tools.wikidata_namen._get",return_value={"search":[]}):
            self.assertEqual(suchname_de("Unbekannter Name"),[])

    def test_ungultige_suchbegriffe(self):
        for text in ("", "a", "x"*121, None):
            with self.subTest(text=text), self.assertRaises(ValueError):
                suchname_de(text)

    def test_ungueltige_id_wird_nicht_abgefragt(self):
        with patch("tools.wikidata_namen._get",return_value={
            "search":[{"id":"Q0;DROP","label":"Pflanze"}]
        }) as fn:
            self.assertEqual(suchname_de("Pflanze"),[])
            self.assertEqual(fn.call_count,1)

    def test_keine_herkunftsverschleierung(self):
        search={"search":[{"id":"Q159219","label":"Hydrangea macrophylla"}]}
        details={"entities":{"Q159219":{"claims":{"P225":[{
            "mainsnak":{"datavalue":{"value":"Hydrangea macrophylla"}}
        }]}}}}
        with patch("tools.wikidata_namen._get",side_effect=[search,details]):
            candidates=suchname_de("Hydrangea macrophylla")
        self.assertIn("wikidata.org/wiki/Q159219",candidates[0]["quelle"])


if __name__=="__main__":
    unittest.main()
