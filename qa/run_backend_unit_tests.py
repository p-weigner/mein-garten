"""Run the pure-Python backend tests with a minimal HA config_validation stub.

The actual Home Assistant installation never contains this file.
This only prevents import-time HA dependencies during isolated unit tests.
Real HA 2026.10 compatibility is independently covered by hassfest and
the Probatio contract check.
"""
from __future__ import annotations

import sys
import types
import unittest


def _bootstrap_stub():
    if "homeassistant" in sys.modules:
        return
    homeassistant = types.ModuleType("homeassistant")
    homeassistant.__path__ = []
    helpers = types.ModuleType("homeassistant.helpers")
    helpers.__path__ = []
    validation = types.ModuleType("homeassistant.helpers.config_validation")
    validation.config_entry_only_config_schema = lambda _domain: lambda value: value
    homeassistant.helpers = helpers
    helpers.config_validation = validation
    sys.modules["homeassistant"] = homeassistant
    sys.modules["homeassistant.helpers"] = helpers
    sys.modules["homeassistant.helpers.config_validation"] = validation


def main():
    _bootstrap_stub()
    suite = unittest.TestLoader().discover("tests")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    main()
