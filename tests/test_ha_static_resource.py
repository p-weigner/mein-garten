"""Statische Gartenkarte wird nur unter eigener URL registriert."""
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from custom_components.mein_garten import async_setup


class FakeStaticPathConfig:
    def __init__(self, url_path, path, cache_headers=False):
        self.url_path = url_path
        self.path = path
        self.cache_headers = cache_headers


class TestStatischesGartenFrontend(unittest.IsolatedAsyncioTestCase):
    async def test_eigene_url_und_keine_dashboard_aenderung(self):
        http = types.ModuleType("homeassistant.components.http")
        http.StaticPathConfig = FakeStaticPathConfig
        components = types.ModuleType("homeassistant.components")
        components.http = http
        ha = types.ModuleType("homeassistant")
        ha.components = components
        mock_api = types.ModuleType("custom_components.mein_garten.api")
        registered = []
        mock_api.registriere_ws_befehle = lambda hass: registered.append(True)

        hass = types.SimpleNamespace(
            data={},
            http=types.SimpleNamespace(async_register_static_paths=AsyncMock()),
        )
        with patch.dict(sys.modules, {
            "homeassistant": ha,
            "homeassistant.components": components,
            "homeassistant.components.http": http,
            "custom_components.mein_garten.api": mock_api,
        }):
            self.assertTrue(await async_setup(hass, {}))
            self.assertTrue(await async_setup(hass, {}))

        hass.http.async_register_static_paths.assert_awaited_once()
        args = hass.http.async_register_static_paths.await_args.args[0]
        self.assertEqual(len(args), 1)
        self.assertEqual(
            args[0].url_path, "/api/mein_garten/mein-garten-v1-card.js"
        )
        self.assertTrue(Path(args[0].path).is_file())
        self.assertEqual(len(registered), 1)
        self.assertNotIn("lovelace", hass.data)
        self.assertNotIn("zuhause", hass.data)


if __name__ == "__main__":
    unittest.main()
