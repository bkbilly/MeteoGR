"""The Meteo.gr integration."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import MeteoGrScraper
from .const import CONF_CITY_ID, CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL, DOMAIN
from .coordinator import MeteoGrDataUpdateCoordinator

PLATFORMS = ["sensor", "weather"]


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the config entry when options are updated."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Meteo.gr from a config entry."""
    session = async_get_clientsession(hass)
    city_id = entry.data[CONF_CITY_ID]

    # Get update interval from options, or use default
    update_interval = entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)

    api = MeteoGrScraper(session, city_id)

    # Pass the update_interval to the coordinator
    coordinator = MeteoGrDataUpdateCoordinator(hass, api, update_interval)

    await coordinator.async_config_entry_first_refresh()

    unsub_listener = entry.add_update_listener(async_reload_entry)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "coordinator": coordinator,
        "unsub_listener": unsub_listener,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload platforms and remove the listener
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        entry_data = hass.data[DOMAIN].pop(entry.entry_id)
        entry_data["unsub_listener"]()  # Call the unsubscribe function

    return unload_ok
