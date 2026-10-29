"""Prüft WebSocket-Daten gegen das echte Probatio 0.13 (HA 2026.10).

Testmodul läuft getrennt, damit der Haupttestlauf ohne fremde HA-Abhängigkeiten
weiterhin schnell und deterministisch bleibt.
"""
import importlib
import sys
import types
from unittest.mock import patch

import probatio


SCHEMAS = {}


def _websocket_command(schema):
    # Home Assistant 2026.10 erwartet den raw-type-Key, danach ein Probatio-Schema.
    command = schema["type"]
    if len(schema) > 1:
        compiled = probatio.Schema(schema)
    else:
        compiled = None
    SCHEMAS[command] = compiled

    def decorate(func):
        return func
    return decorate


def main():
    ha = types.ModuleType("homeassistant")
    components = types.ModuleType("homeassistant.components")
    ws = types.ModuleType("homeassistant.components.websocket_api")
    ws.websocket_command = _websocket_command
    ws.async_response = lambda func: func
    ws.async_register_command = lambda *args: None
    components.websocket_api = ws
    ha.components = components
    core = types.ModuleType("homeassistant.core")
    core.callback = lambda func: func
    ha.core = core
    helpers = types.ModuleType("homeassistant.helpers")
    config_validation = types.ModuleType("homeassistant.helpers.config_validation")
    config_validation.config_entry_only_config_schema = lambda domain: lambda value: value
    helpers.config_validation = config_validation
    dispatcher = types.ModuleType("homeassistant.helpers.dispatcher")
    dispatcher.async_dispatcher_connect = lambda *args: None
    helpers.dispatcher = dispatcher
    ha.helpers = helpers

    with patch.dict(sys.modules, {
        "homeassistant": ha,
        "homeassistant.components": components,
        "homeassistant.components.websocket_api": ws,
        "homeassistant.core": core,
        "homeassistant.helpers": helpers,
        "homeassistant.helpers.config_validation": config_validation,
        "homeassistant.helpers.dispatcher": dispatcher,
    }):
        sys.modules.pop("custom_components.mein_garten.api", None)
        importlib.import_module("custom_components.mein_garten.api")
        sys.modules.pop("custom_components.mein_garten.api", None)

    assert len(SCHEMAS) >= 13, "Nicht alle Garten-WS-Befehle registriert"
    expected = {
        "mein_garten/pflanzen_suchen": {
            "type": "mein_garten/pflanzen_suchen",
            "suchbegriff": "Bauernhortensie",
        },
        "mein_garten/pflanze_anlegen": {
            "type": "mein_garten/pflanze_anlegen",
            "name": "Meine Bauernhortensie",
            "wissenschaftlich": "Hydrangea macrophylla",
            "gruppe": None,
            "bereich_id": None,
            "notizen": "",
        },
        "mein_garten/aufgabe_anlegen": {
            "type": "mein_garten/aufgabe_anlegen",
            "name": "Gießen",
            "faellig_am": None,
            "pflanzen_id": None,
            "bereich_id": None,
        },
    }
    for key, msg in expected.items():
        assert key in SCHEMAS, key
        schema = SCHEMAS[key]
        assert schema is not None
        valid = schema(msg)
        assert valid["type"] == key, (key, valid)

    try:
        SCHEMAS["mein_garten/pflanzen_suchen"]({
            "type": "mein_garten/pflanzen_suchen",
            "suchbegriff": 15,
        })
    except probatio.Invalid:
        pass
    else:
        raise AssertionError("Ungültiger Suchbegriff wurde nicht zurückgewiesen")

    try:
        SCHEMAS["mein_garten/pflanze_anlegen"]({
            "type": "mein_garten/pflanze_anlegen",
            "name": 123,
        })
    except probatio.Invalid:
        pass
    else:
        raise AssertionError("Ungültiger Pflanzenname wurde nicht zurückgewiesen")

    print("Probatio 0.13: 13+ WS-Befehle kompiliert, Eingaben und Fehlertypen geprüft.")


if __name__ == "__main__":
    main()
