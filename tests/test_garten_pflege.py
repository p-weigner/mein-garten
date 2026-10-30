"""Isolierte Sicherheits- und Vertragsprüfungen der Pflegeprofilverarbeitung."""
import asyncio
from copy import deepcopy
from datetime import timedelta
import unittest
from unittest.mock import AsyncMock, MagicMock
from custom_components.mein_garten.care import (
    CARE_FIELDS, PflegeService, _same_species, _segments, _source_field, _valid_species, _now,
)


class TestPflegeDaten(unittest.TestCase):
    def test_botanischer_artabgleich_ohne_stille_ersatzart(self):
        self.assertTrue(_same_species("Fragaria × ananassa", "Fragaria x ananassa"))
        self.assertFalse(_same_species("Hydrangea macrophylla", "Hydrangea paniculata"))
        self.assertTrue(_valid_species("Lavandula angustifolia"))
        self.assertFalse(_valid_species("Bauernhortensie"))

    def test_uebersetzungssegmente_bleiben_im_limit(self):
        pieces = _segments(("Water when the soil is dry. " * 200).strip())
        self.assertTrue(pieces)
        self.assertTrue(all(len(x.encode("utf-8")) <= 500 for x in pieces))

    def test_ungeeignete_fremdtexte_werden_abgewiesen(self):
        self.assertEqual(_source_field("<script>alert(1)</script>"), "")
        self.assertEqual(_source_field("a" * 1800), "")
        self.assertEqual(len(CARE_FIELDS), 5)


class FakeServices:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def has_service(self, domain, service):
        return True

    async def async_call(self, domain, service, data, **kwargs):
        self.calls.append((domain, service, data))
        return self.response[service]


class TestPflegeAbruf(unittest.IsolatedAsyncioTestCase):
    async def test_falsche_art_darf_keine_fremdhinweise_ausgeben(self):
        services = FakeServices({
            "search": {"Hydrangea paniculata": "Hydrangea paniculata"},
            "get": {"pid": "Hydrangea paniculata", "watering": "Often"},
        })
        service = PflegeService.__new__(PflegeService)
        service.hass = MagicMock()
        service.hass.services = services
        result = await service._fetch("Hydrangea macrophylla")
        self.assertEqual(result["status"], "art_nicht_gefunden")
        self.assertEqual([c[1] for c in services.calls], ["search"])

    async def test_pflegehinweise_ohne_automatische_aufgaben(self):
        services = FakeServices({
            "search": {"Hydrangea macrophylla": "Hydrangea macrophylla"},
            "get": {
                "pid": "Hydrangea macrophylla",
                "watering": "Water regularly",
                "sunlight": "Partial shade",
                "soil": "Moist soil",
                "pruning": "Prune only carefully",
                "fertilization": "Fertilize when needed",
            },
        })
        service = PflegeService.__new__(PflegeService)
        service.hass = MagicMock()
        service.hass.services = services
        service._deutscher_text = AsyncMock(side_effect=lambda species, field, raw: "DE " + raw)
        result = await service._fetch("Hydrangea macrophylla")
        self.assertEqual(result["status"], "ok")
        self.assertFalse(result["automatische_aufgaben_erlaubt"])
        self.assertEqual(len(result["felder"]), 5)
        self.assertEqual(services.calls[-1][2]["include"], "care")
        self.assertEqual(result["felder"]["pruning"]["status"], "maschinenuebersetzt")

    async def test_teiluebersetztes_profil_wird_nicht_30_tage_blockiert(self):
        services = FakeServices({
            "search": {"Lavandula angustifolia": "Lavandula angustifolia"},
            "get": {
                "pid": "Lavandula angustifolia",
                "watering": "Water occasionally",
                "soil": "Well-drained soil",
            },
        })
        service = PflegeService.__new__(PflegeService)
        service.hass = MagicMock()
        service.hass.services = services
        service._deutscher_text = AsyncMock(
            side_effect=lambda species, field, raw: "Wenig gießen" if field == "watering" else None
        )
        result = await service._fetch("Lavandula angustifolia")
        self.assertEqual(result["status"], "teilweise")
        self.assertEqual(result["felder"]["watering"]["text"], "Wenig gießen")
        self.assertIsNone(result["felder"]["soil"]["text"])

    async def test_bereits_deutsche_quelltexte_keine_englischnachuebersetzung(self):
        services = FakeServices({
            "search": {"Lavandula angustifolia": "Lavandula angustifolia"},
            "get": {
                "pid": "Lavandula angustifolia",
                "lang": "de",
                "watering": "Gießen, sobald der Boden trocken ist.",
            },
        })
        service = PflegeService.__new__(PflegeService)
        service.hass = MagicMock()
        service.hass.services = services
        service._deutscher_text = AsyncMock()
        result = await service._fetch("Lavandula angustifolia")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["felder"]["watering"]["status"], "original_deutsch")
        service._deutscher_text.assert_not_awaited()

    async def test_uebersetzte_teilfelder_ueberleben_cache_refresh(self):
        class Store:
            def __init__(self):
                self.saved = None
            async def async_save(self, data):
                self.saved = deepcopy(data)

        services = FakeServices({
            "search": {"Lavandula angustifolia": "Lavandula angustifolia"},
            "get": {
                "pid": "Lavandula angustifolia",
                "watering": "Water moderately",
                "soil": "Well-drained soil",
            },
        })
        service = PflegeService.__new__(PflegeService)
        service.hass = MagicMock()
        service.hass.services = services
        service._store = Store()
        service._lock = asyncio.Lock()
        service._data = {
            "version": 1, "profile": {}, "budget": {"tag": "", "zeichen": 0},
            "translations": {},
        }

        used = []
        async def first_try(text):
            used.append(text)
            return "Mäßig gießen" if text == "Water moderately" else None
        service._translate = first_try
        first = await service.async_profil({"wissenschaftlich": "Lavandula angustifolia"})
        self.assertEqual(first["status"], "teilweise")
        self.assertEqual(len(used), 2)
        self.assertEqual(len(service._data["translations"]), 1)

        cached = await service.async_profil({"wissenschaftlich": "Lavandula angustifolia"})
        self.assertEqual(cached["status"], "teilweise")
        self.assertEqual(len(used), 2)

        # Kürzere Cachefrist nachweisen, ohne Netzwerk oder Host-Uhr zu manipulieren.
        service._data["profile"]["lavandula angustifolia"]["abgerufen_utc"] = (
            _now() - timedelta(hours=19)
        ).isoformat()
        service._translate = AsyncMock(return_value="Durchlässiger Boden")
        second = await service.async_profil({"wissenschaftlich": "Lavandula angustifolia"})
        self.assertEqual(second["status"], "ok")
        self.assertEqual(second["felder"]["watering"]["text"], "Mäßig gießen")
        self.assertEqual(second["felder"]["soil"]["text"], "Durchlässiger Boden")
        service._translate.assert_awaited_once_with("Well-drained soil")
        self.assertEqual(len(service._data["translations"]), 2)
        self.assertNotIn("Water moderately", str(service._store.saved))

    async def test_abweichender_detail_pid_wird_abgelehnt(self):
        services = FakeServices({
            "search": {"Hydrangea macrophylla": "Hydrangea macrophylla"},
            "get": {"pid": "Hydrangea paniculata", "watering": "Water regularly"},
        })
        service = PflegeService.__new__(PflegeService)
        service.hass = MagicMock()
        service.hass.services = services
        result = await service._fetch("Hydrangea macrophylla")
        self.assertEqual(result["status"], "art_nicht_bestaetigt")


class TestPflegeManuelleAktualisierung(unittest.IsolatedAsyncioTestCase):
    """Quelle wieder prüfen, ohne deutsche Cachetexte oder Tagesbudget zu verlieren."""

    def make_service(self):
        class Store:
            def __init__(self):
                self.saved = []
            async def async_save(self, data):
                self.saved.append(deepcopy(data))

        service = PflegeService.__new__(PflegeService)
        service.hass = MagicMock()
        service._store = Store()
        service._lock = asyncio.Lock()
        service._data = {
            "version": 1,
            "profile": {},
            "budget": {"tag": "", "zeichen": 170},
            "translations": {},
        }
        return service

    def result(self, service, text, status="ok"):
        return service._result(
            "Rosa canina", status,
            {"watering": {"titel": "Gießen", "text": text,
                           "status": "maschinenuebersetzt"}},
        )

    async def test_normale_cache_gültigkeit_und_erzwungener_abruf(self):
        service = self.make_service()
        service._fetch = AsyncMock(side_effect=[
            self.result(service, "Ein deutscher Hinweis"),
            self.result(service, "Aktualisierter deutscher Hinweis"),
        ])
        plant = {"wissenschaftlich": "Rosa canina"}
        first = await service.async_profil(plant)
        self.assertEqual(first["felder"]["watering"]["text"], "Ein deutscher Hinweis")
        from_cache = await service.async_profil(plant)
        self.assertEqual(from_cache, first)
        service._fetch.assert_awaited_once()
        fresh = await service.async_profil(plant, aktualisieren=True)
        self.assertEqual(fresh["felder"]["watering"]["text"], "Aktualisierter deutscher Hinweis")
        self.assertEqual(service._fetch.await_count, 2)
        self.assertEqual(service._data["budget"]["zeichen"], 170)
        self.assertEqual(len(service._store.saved), 2)

    async def test_erneuter_klick_erzwingt_keinen_api_spam(self):
        service = self.make_service()
        service._fetch = AsyncMock(return_value=self.result(service, "Deutscher Hinweis"))
        plant = {"wissenschaftlich": "Rosa canina"}
        await service.async_profil(plant, aktualisieren=True)
        repeated = await service.async_profil(plant, aktualisieren=True)
        self.assertEqual(service._fetch.await_count, 1)
        self.assertEqual(repeated["aktualisierung"], "wartezeit")
        self.assertEqual(repeated["felder"]["watering"]["text"], "Deutscher Hinweis")
        # Nur der Prüfversuch wird gedrosselt: bestehende Profile sind weiter lesbar.
        normal = await service.async_profil(plant)
        self.assertEqual(normal["status"], "ok")
        self.assertNotIn("aktualisierung", normal)

    async def test_abgelaufene_sperre_ermöglicht_erneuten_abruf(self):
        service = self.make_service()
        service._fetch = AsyncMock(return_value=self.result(service, "Deutscher Hinweis"))
        plant = {"wissenschaftlich": "Rosa canina"}
        await service.async_profil(plant, aktualisieren=True)
        service._auffrischungen["rosa canina"] = _now() - timedelta(minutes=6)
        await service.async_profil(plant, aktualisieren=True)
        self.assertEqual(service._fetch.await_count, 2)

    async def test_ausfall_erhält_übersetzte_texte_ohne_store_überschreiben(self):
        for failed in ("quelle_nicht_erreichbar", "quelle_nicht_eingerichtet",
                       "quellenantwort_ungueltig", "art_nicht_gefunden",
                       "kein_deutscher_text"):
            with self.subTest(failed=failed):
                service = self.make_service()
                prior = self.result(service, "Gespeicherter deutscher Text")
                prior["abgerufen_utc"] = (
                    _now() - timedelta(days=31)
                ).isoformat(timespec="seconds")
                service._data["profile"]["rosa canina"] = prior
                service._fetch = AsyncMock(
                    return_value=service._result("Rosa canina", failed)
                )
                result = await service.async_profil(
                    {"wissenschaftlich": "Rosa canina"}, aktualisieren=True
                )
                self.assertEqual(result["aktualisierung"], failed)
                self.assertEqual(
                    result["felder"]["watering"]["text"],
                    "Gespeicherter deutscher Text",
                )
                self.assertEqual(
                    service._data["profile"]["rosa canina"], prior
                )
                self.assertEqual(len(service._store.saved), 0)

    async def test_neue_vollständige_quelle_ersetzt_alte_teilangaben(self):
        service = self.make_service()
        prior = self.result(service, "Alter Hinweis", "teilweise")
        service._data["profile"]["rosa canina"] = prior
        service._fetch = AsyncMock(return_value=self.result(service, "Neu belegt"))
        fresh = await service.async_profil(
            {"wissenschaftlich": "Rosa canina"}, aktualisieren=True
        )
        self.assertEqual(fresh["status"], "ok")
        self.assertEqual(fresh["felder"]["watering"]["text"], "Neu belegt")
        self.assertNotIn("aktualisierung", fresh)
        self.assertEqual(len(service._store.saved), 1)

    async def test_falsche_flagtypen_und_unbekannte_arten_abgelehnt(self):
        service = self.make_service()
        service._fetch = AsyncMock()
        with self.assertRaises(ValueError):
            await service.async_profil(
                {"wissenschaftlich": "Rosa canina"}, aktualisieren=1
            )
        missing = await service.async_profil(
            {"wissenschaftlich": ""}, aktualisieren=True
        )
        self.assertEqual(missing["status"], "art_unbekannt")
        service._fetch.assert_not_awaited()


class TestPflegeTeilantworten(unittest.IsolatedAsyncioTestCase):
    """Einzelfeld-Historie für teilweise fehlende Pflegeinformationen."""

    make_service = TestPflegeManuelleAktualisierung.make_service
    result = TestPflegeManuelleAktualisierung.result

    def _prepare(self, service):
        previous = service._result("Rosa canina", "ok", {
            "watering": {
                "titel": "Gießen", "text": "Früher sparsam gießen",
                "status": "maschinenuebersetzt", "quelle": "OpenPlantbook",
            },
            "pruning": {
                "titel": "Schnitt", "text": "Historischer Schnitthinweis",
                "status": "maschinenuebersetzt", "quelle": "OpenPlantbook",
            },
        })
        previous["abgerufen_utc"] = "2026-10-01T10:00:00+00:00"
        service._data["profile"]["rosa canina"] = deepcopy(previous)
        return previous

    async def test_aktuelle_wasserangabe_und_alter_schnitt_separat_markiert(self):
        service = self.make_service()
        self._prepare(service)
        update = service._result("Rosa canina", "teilweise", {
            "watering": {
                "titel": "Gießen", "text": "Neue deutsche Bewässerungsinfo",
                "status": "original_deutsch", "quelle": "OpenPlantbook",
            },
            "pruning": {
                "titel": "Schnitt", "text": None,
                "status": "uebersetzung_ausstehend", "quelle": "OpenPlantbook",
            },
        })
        service._fetch = AsyncMock(return_value=update)
        result = await service.async_profil(
            {"wissenschaftlich": "Rosa canina"}, aktualisieren=True
        )
        self.assertEqual(result["status"], "teilweise")
        self.assertEqual(result["veraltete_felder"], 1)
        self.assertEqual(result["felder"]["watering"]["text"], "Neue deutsche Bewässerungsinfo")
        self.assertNotEqual(result["felder"]["watering"]["status"], "zwischengespeichert")
        self.assertEqual(
            result["felder"]["watering"]["belegt_utc"], update["abgerufen_utc"]
        )
        old = result["felder"]["pruning"]
        self.assertEqual(old["status"], "zwischengespeichert")
        self.assertEqual(old["quellstatus"], "uebersetzung_ausstehend")
        self.assertEqual(old["text"], "Historischer Schnitthinweis")
        self.assertEqual(old["zuletzt_bestaetigt_utc"], "2026-10-01T10:00:00+00:00")
        self.assertFalse(result["automatische_aufgaben_erlaubt"])
        self.assertEqual(service._store.saved[-1]["profile"]["rosa canina"], result)

    async def test_neu_geladener_schnitt_ersetzt_zwischengespeicherten_text(self):
        service = self.make_service()
        self._prepare(service)
        first = service._result("Rosa canina", "teilweise", {
            "watering": {"titel": "Gießen", "text": "Neu", "status": "maschinenuebersetzt"},
            "pruning": {"titel": "Schnitt", "text": None, "status": "keine_angabe"},
        })
        second = service._result("Rosa canina", "ok", {
            "watering": {"titel": "Gießen", "text": "Aktueller Wasserhinweis",
                         "status": "maschinenuebersetzt"},
            "pruning": {"titel": "Schnitt", "text": "Neuer Schnitthinweis",
                        "status": "maschinenuebersetzt"},
        })
        service._fetch = AsyncMock(side_effect=[first, second])
        await service.async_profil({"wissenschaftlich": "Rosa canina"}, aktualisieren=True)
        service._auffrischungen["rosa canina"] = _now() - timedelta(minutes=6)
        result = await service.async_profil(
            {"wissenschaftlich": "Rosa canina"}, aktualisieren=True
        )
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["felder"]["pruning"]["text"], "Neuer Schnitthinweis")
        self.assertNotIn("zuletzt_bestaetigt_utc", result["felder"]["pruning"])
        self.assertNotIn("veraltete_felder", result)

    async def test_alter_zeitpunkt_wird_bei_wiederholten_teilantworten_nicht_geaendert(self):
        service = self.make_service()
        self._prepare(service)
        def partial():
            return service._result("Rosa canina", "teilweise", {
                "watering": {"titel": "Gießen", "text": "Heute aktuell",
                             "status": "maschinenuebersetzt"},
                "pruning": {"titel": "Schnitt", "text": None,
                            "status": "keine_angabe"},
            })
        service._fetch = AsyncMock(side_effect=[partial(), partial()])
        first = await service.async_profil(
            {"wissenschaftlich": "Rosa canina"}, aktualisieren=True
        )
        service._auffrischungen["rosa canina"] = _now() - timedelta(minutes=6)
        second = await service.async_profil(
            {"wissenschaftlich": "Rosa canina"}, aktualisieren=True
        )
        for item in (first, second):
            self.assertEqual(
                item["felder"]["pruning"]["zuletzt_bestaetigt_utc"],
                "2026-10-01T10:00:00+00:00"
            )
        self.assertEqual(second["veraltete_felder"], 1)

    async def test_fehlen_einzelner_kompletter_felder_wird_als_alt_markiert(self):
        service = self.make_service()
        self._prepare(service)
        service._fetch = AsyncMock(return_value=service._result(
            "Rosa canina", "ok", {
                "watering": {"titel": "Gießen", "text": "Aktuell",
                             "status": "original_deutsch"},
            }
        ))
        result = await service.async_profil(
            {"wissenschaftlich": "Rosa canina"}, aktualisieren=True
        )
        self.assertEqual(result["status"], "teilweise")
        self.assertEqual(result["felder"]["pruning"]["status"], "zwischengespeichert")
        self.assertEqual(result["felder"]["pruning"]["quellstatus"], "keine_angabe")
        self.assertEqual(result["veraltete_felder"], 1)

    async def test_veralteter_fremder_arten_oder_quellentext_wird_nicht_gemischt(self):
        service = self.make_service()
        current = service._result("Rosa canina", "teilweise", {
            "watering": {"titel": "Gießen", "text": "Neu", "status": "original_deutsch"},
            "pruning": {"titel": "Schnitt", "text": None, "status": "keine_angabe"},
        })
        previous = service._result("Rosa rugosa", "ok", {
            "pruning": {"titel": "Schnitt", "text": "Nur für eine andere Art"},
        })
        self.assertEqual(service._alte_teilfelder_sichern(current, previous), 0)
        self.assertIsNone(current["felder"]["pruning"]["text"])
        previous["art"] = "Rosa canina"
        previous["quelle"] = "Andere Quelle"
        self.assertEqual(service._alte_teilfelder_sichern(current, previous), 0)
        self.assertIsNone(current["felder"]["pruning"]["text"])

    async def test_feld_mit_fremder_quelle_und_leerem_text_wird_nicht_uebernommen(self):
        service = self.make_service()
        current = service._result("Rosa canina", "teilweise", {
            "watering": {"titel": "Gießen", "text": "Neuer Hinweis"},
            "pruning": {"titel": "Schnitt", "text": None, "status": "keine_angabe"},
        })
        old = service._result("Rosa canina", "ok", {
            "pruning": {
                "titel": "Schnitt", "text": "Fremder Hinweis",
                "quelle": "Andere Quelle",
            },
        })
        self.assertEqual(service._alte_teilfelder_sichern(current, old), 0)
        self.assertIsNone(current["felder"]["pruning"]["text"])
        old["felder"]["pruning"]["quelle"] = "OpenPlantbook"
        old["felder"]["pruning"]["text"] = "x" * 12001
        self.assertEqual(service._alte_teilfelder_sichern(current, old), 0)
        self.assertIsNone(current["felder"]["pruning"]["text"])


if __name__ == "__main__":
    unittest.main()
