"""CraftBeerPi 4 voor Home Assistant (via de REST-API, geen MQTT nodig)."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import CBPiClient
from .const import CONF_PASSWORD, CONF_SCAN_INTERVAL, CONF_URL, CONF_USERNAME, DEFAULT_SCAN_INTERVAL, DOMAIN, PLATFORMS
from .coordinator import CBPiCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    client = CBPiClient(async_get_clientsession(hass), entry.data[CONF_URL], entry.data.get(CONF_USERNAME), entry.data.get(CONF_PASSWORD))
    interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    coord = CBPiCoordinator(hass, client, interval, entry)
    await coord.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coord
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_reload))
    return True


async def _reload(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return ok
