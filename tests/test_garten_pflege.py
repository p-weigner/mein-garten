"""Isolierte Sicherheits- und Vertragsprüfungen der Pflegeprofilverarbeitung."""
import unittest
from unittest.mock import AsyncMock, MagicMock
from custom_components.mein_garten.care import (
    CARE_FIELDS, PflegeService, _same_species, _segments, _source_field, _valid_species,
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
        service._translate = AsyncMock(side_effect=lambda x: "DE " + x)
        result = await service._fetch("Hydrangea macrophylla")
        self.assertEqual(result["status"], "ok")
        self.assertFalse(result["automatische_aufgaben_erlaubt"])
        self.assertEqual(len(result["felder"]), 5)
        self.assertEqual(services.calls[-1][2]["include"], "care")
        self.assertEqual(result["felder"]["pruning"]["status"], "maschinenuebersetzt")

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


if __name__ == "__main__":
    unittest.main()
