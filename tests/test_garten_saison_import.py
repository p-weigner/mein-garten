"""Offline-Tests der OpenPlantDB-Quelle: keine stillen Sorten-Mittelwerte."""
from unittest import TestCase
from tools.openplantdb_katalog_export import make_catalog, UPSTREAM_COMMIT
from custom_components.mein_garten.season import pruefe_katalog, SaisonFehler


def sample(species, slug, lo, hi, method="transplant", category="flower"):
    return {
        "slug": slug,
        "scientific_name": species,
        "category": category,
        "planting": {
            "anchor": "last_frost",
            "weeks_from_anchor": {"min": lo, "max": hi},
        },
        "sow_method": method,
    }


class TestOpenPlantDBImport(TestCase):
    def test_eindeutige_art_wird_als_offline_regel_uebernommen(self):
        result, report = make_catalog([
            sample("Buddleja davidii", "buddleja", 0, 4),
        ], [])
        self.assertEqual(report["neue_eindeutige_arten"], 1)
        record = result["regeln"][0]
        self.assertEqual(record["id"], "opdb26-buddleja-davidii")
        self.assertEqual(record["wissenschaftlich"], "Buddleja davidii")
        self.assertEqual(record["methode"], "transplant")
        self.assertEqual(result["ausgangs_commit"], UPSTREAM_COMMIT)
        self.assertEqual(len(pruefe_katalog(result)), 1)

    def test_mehrere_identische_quellenhinweise_erzeugen_nur_eine_regel(self):
        records = [
            sample("Buddleja davidii", "buddleja-white", 0, 4),
            sample("Buddleja davidii", "buddleja-pink", 0, 4),
        ]
        result, report = make_catalog(records, [])
        self.assertEqual(report["neue_eindeutige_arten"], 1)
        self.assertEqual(len(result["regeln"]), 1)

    def test_widerspruch_bei_anbaumethoden_oder_wochen_sperrt_regel(self):
        records = [
            sample("Capsicum annuum", "paprika-red", -8, -6, "indoor-start"),
            sample("Capsicum annuum", "paprika-purple", -10, -8, "indoor-start"),
            sample("Buddleja davidii", "sommerflieder", 0, 4),
        ]
        result, report = make_catalog(records, [])
        self.assertEqual(report["ausgeschlossene_arten_mit_widerspruch"], 1)
        self.assertEqual([r["wissenschaftlich"] for r in result["regeln"]],
                         ["Buddleja davidii"])

    def test_alter_katalog_wird_nicht_unbemerkt_ueberschrieben(self):
        result, report = make_catalog([
            sample("Solanum lycopersicum", "tomato", -8, -6, "indoor-start"),
            sample("Buddleja davidii", "butterfly-bush", 0, 4),
        ], [{"wissenschaftlich": "Solanum lycopersicum"}])
        self.assertEqual(report["bereits_im_basiskatalog"], 1)
        self.assertEqual([r["wissenschaftlich"] for r in result["regeln"]],
                         ["Buddleja davidii"])

    def test_ungueltige_botanische_bezeichnungen_werden_nicht_erraten(self):
        result, _ = make_catalog([
            sample("Buddleja davidii", "buddleja", 0, 4),
            sample("Malus domestica 'Golden Delicious'", "golden-apple", 0, 4),
            sample("Rosa", "rosa", 0, 4),
        ], [])
        self.assertEqual(len(result["regeln"]), 1)

    def test_keine_gueltigen_regeln_ist_harter_fehler(self):
        with self.assertRaises(ValueError):
            make_catalog([
                sample("Solanum lycopersicum", "tomato", -8, -6, "indoor-start"),
            ], [{"wissenschaftlich": "Solanum lycopersicum"}])

    def test_boolean_wochenzahlen_sind_unzulaessig(self):
        result, _ = make_catalog([
            sample("Buddleja davidii", "buddleja", 0, 4),
            sample("Cucumis sativus", "cucumber", True, 3),
        ], [])
        self.assertEqual(len(result["regeln"]), 1)
