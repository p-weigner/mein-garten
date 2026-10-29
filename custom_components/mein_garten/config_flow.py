"""Minimaler UI-Einrichtungsdialog ohne zusätzliche API-Schlüssel."""

from homeassistant import config_entries
import voluptuous as vol

from .const import DOMAIN


class MeinGartenConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Die Integration kann nur einmal eingerichtet werden."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Einmaliges Einrichten durch Home Assistant."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")
        if user_input is not None:
            return self.async_create_entry(title="Mein Garten", data={})
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({}),
        )
