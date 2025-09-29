"""Config flow for Meteo.gr integration."""

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import MeteoGrScraper
from .const import (
    CONF_CITY_ID,
    CONF_STATION_NAME,
    CONF_UPDATE_INTERVAL,  # ADDED
    DEFAULT_UPDATE_INTERVAL,  # ADDED
    DOMAIN,
)


class MeteoGrOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle an options flow for Meteo.gr."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Get the current value or the default
        current_interval = self.config_entry.options.get(
            CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_UPDATE_INTERVAL, default=current_interval): int,
                }
            ),
        )


class MeteoGrConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Meteo.gr."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> MeteoGrOptionsFlowHandler:
        """Get the options flow for this handler."""
        return MeteoGrOptionsFlowHandler(config_entry)

    def __init__(self) -> None:
        """Initialize the config flow."""
        self.data: dict[str, Any] = {}
        self.stations: list[str] = []

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            city_id = user_input[CONF_CITY_ID]
            session = async_get_clientsession(self.hass)

            api = MeteoGrScraper(session, city_id)
            if await api.update() and api.live_stations:
                self.data[CONF_CITY_ID] = city_id
                self.stations = [station["name"] for station in api.live_stations]
                return await self.async_step_station()

            errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_CITY_ID): int}),
            errors=errors,
        )

    async def async_step_station(self, user_input=None):
        """Handle the station selection step."""
        if user_input is not None:
            self.data[CONF_STATION_NAME] = user_input[CONF_STATION_NAME]
            await self.async_set_unique_id(
                f"{self.data[CONF_CITY_ID]}_{self.data[CONF_STATION_NAME]}"
            )
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=self.data[CONF_STATION_NAME], data=self.data
            )

        return self.async_show_form(
            step_id="station",
            data_schema=vol.Schema(
                {vol.Required(CONF_STATION_NAME): vol.In(self.stations)}
            ),
        )
