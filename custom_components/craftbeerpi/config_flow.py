"""Instellen via de UI."""
from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import CBPiAuthError, CBPiClient, CBPiError
from .const import CONF_PASSWORD, CONF_SCAN_INTERVAL, CONF_URL, CONF_USERNAME, DEFAULT_SCAN_INTERVAL, DOMAIN


class CBPiConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input:
            url = user_input[CONF_URL].strip().rstrip("/")
            client = CBPiClient(async_get_clientsession(self.hass), url, user_input.get(CONF_USERNAME) or None, user_input.get(CONF_PASSWORD))
            try:
                await client.get("/fermenter/")
            except CBPiAuthError:
                errors["base"] = "invalid_auth"
            except CBPiError:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(url.lower())
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title="CraftBeerPi", data={**user_input, CONF_URL: url})
        schema = vol.Schema({
            vol.Required(CONF_URL, default="http://192.168.1.76:8000"): str,
            vol.Optional(CONF_USERNAME): str,
            vol.Optional(CONF_PASSWORD): str,
        })
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    def async_get_options_flow(entry):
        return CBPiOptionsFlow()


class CBPiOptionsFlow(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        cur = self.config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        return self.async_show_form(step_id="init", data_schema=vol.Schema({vol.Required(CONF_SCAN_INTERVAL, default=cur): vol.All(int, vol.Range(min=5, max=600))}))
