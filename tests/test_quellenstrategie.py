import unittest

from tools.pflegewissen import Pflegehinweis, ArtNichtPassend
from tools.quellenstrategie import kombiniere_pflegewissen


def sample(
    art="Hydrangea macrophylla",
    feld="pruning",
    quelle="OpenPlantbook",
    orig="Avoid severe pruning",
    deutsch="Keine starken Rückschnitte",
    quid="hydrangea macrophylla",
):
    return Pflegehinweis(
        art=art,
        feld=feld,
        original=orig,
        sprache_original="en",
        quelle=quelle,
        quell_id=quid,
        quell_url="https://example.org/source",
        lizenz_hinweis="Beispieltext, nicht produktiv",
        abgerufen_utc="2026-10-29T00:00:00Z",
        deutsch=deutsch,
        uebersetzung="automatisch" if deutsch else "ausstehend",
    )


class TestDynamischeQuellenstrategie(unittest.TestCase):
    def test_beliebige_art_ohne_codeaenderung(self):
        profil=kombiniere_pflegewissen(
            "Paeonia lactiflora",
            [sample(art="Paeonia lactiflora", feld="watering")],
        )
        self.assertEqual(profil["art"], "Paeonia lactiflora")
        self.assertEqual(profil["felder"]["watering"]["status"], "uebersetzung_vorhanden")

    def test_falsche_art_wird_nicht_vermischt(self):
        with self.assertRaises(ArtNichtPassend):
            kombiniere_pflegewissen(
                "Hydrangea macrophylla",
                [sample(art="Hydrangea paniculata")],
            )

    def test_kein_scheinwissen_bei_unbekannter_art(self):
        profil=kombiniere_pflegewissen("Paeonia lactiflora",[])
        self.assertEqual(profil["pflegefelder_mit_deutschem_text"],0)
        self.assertTrue(all(x["status"]=="keine_quelle" for x in profil["felder"].values()))

    def test_kein_englischer_text_als_deutsche_anzeige(self):
        item=sample(orig="Prune in spring",deutsch=None)
        profil=kombiniere_pflegewissen("Hydrangea macrophylla",[item])
        feld=profil["felder"]["pruning"]
        self.assertIsNone(feld["text_de"])
        self.assertEqual(feld["status"],"uebersetzung_ausstehend")
        self.assertIsNone(feld["quellen"][0]["text_de"])

    def test_eigene_hinweise_haben_vorrang(self):
        profil=kombiniere_pflegewissen(
            "Hydrangea macrophylla",
            [sample()],
            eigene_hinweise={"pruning":"Meine persönliche Beobachtung"},
        )
        feld=profil["felder"]["pruning"]
        self.assertEqual(feld["text_de"],"Meine persönliche Beobachtung")
        self.assertEqual(feld["anzeigequelle"],"Eigener Hinweis")
        self.assertEqual(feld["quellen"][0]["text_de"],"Keine starken Rückschnitte")

    def test_fallback_wenn_erste_quelle_nicht_uebersetzt(self):
        one=sample(deutsch=None)
        two=sample(quelle="Permapeople",orig="Less is more",deutsch="Sparsam schneiden")
        profil=kombiniere_pflegewissen("Hydrangea macrophylla",[two,one])
        feld=profil["felder"]["pruning"]
        self.assertEqual(feld["text_de"],"Sparsam schneiden")
        self.assertEqual(feld["anzeigequelle"],"Permapeople")
        self.assertEqual(len(feld["quellen"]),2)
        self.assertEqual(feld["quellen"][0]["quelle"],"OpenPlantbook")

    def test_doppelte_datensaetze_nicht_doppelt_anzeigen(self):
        one=sample()
        two=sample()
        profil=kombiniere_pflegewissen("Hydrangea macrophylla",[one,two])
        self.assertEqual(len(profil["felder"]["pruning"]["quellen"]),1)

    def test_unterschiedliche_quellen_bleiben_getrennt(self):
        one=sample(deutsch="Vorsichtig schneiden")
        two=sample(quelle="Permapeople",orig="Different source",deutsch="Nicht stark schneiden")
        profil=kombiniere_pflegewissen("Hydrangea macrophylla",[two,one])
        feld=profil["felder"]["pruning"]
        self.assertEqual(feld["text_de"],"Vorsichtig schneiden")
        self.assertEqual(len(feld["quellen"]),2)
        self.assertEqual(feld["quellen"][1]["quelle"],"Permapeople")
        self.assertEqual(feld["pruefstatus"],"nicht_fachlich_freigegeben")

    def test_keine_automatische_arbeitsfreigabe(self):
        profil=kombiniere_pflegewissen(
            "Hydrangea macrophylla",
            [sample(),sample(feld="fertilization",orig="Feed often",deutsch="Regelmäßig düngen")],
        )
        self.assertFalse(profil["automatische_pflegeaufgaben_erlaubt"])
        for feld in profil["felder"].values():
            self.assertFalse(feld["automatische_aufgabe_erlaubt"])
            self.assertTrue(all(not v["automatische_aufgabe_erlaubt"] for v in feld["quellen"]))

    def test_unzulaessiges_eigenes_feld_abgelehnt(self):
        with self.assertRaises(ValueError):
            kombiniere_pflegewissen("Hydrangea macrophylla", [], {"safety":"ungültig"})

    def test_leere_spezies_abgelehnt(self):
        with self.assertRaises(ValueError):
            kombiniere_pflegewissen("",[])

    def test_quellenangabe_bleibt_erhalten(self):
        profil=kombiniere_pflegewissen("Hydrangea macrophylla",[sample()])
        r=profil["felder"]["pruning"]["quellen"][0]
        self.assertEqual(r["quell_url"],"https://example.org/source")
        self.assertEqual(r["uebersetzungsstatus"],"automatisch")
        self.assertIn("lizenz_hinweis",r)
        self.assertIn("abgerufen_utc",r)


if __name__=="__main__":
    unittest.main()
