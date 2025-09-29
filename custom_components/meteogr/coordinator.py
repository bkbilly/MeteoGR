"""DataUpdateCoordinator for the Meteo.gr integration."""

from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import MeteoGrScraper
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class MeteoGrDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Meteo.gr data."""

    def __init__(
        self, hass: HomeAssistant, api: MeteoGrScraper, update_interval: int
    ) -> None:
        """Initialize the data update coordinator."""
        self.api = api
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=update_interval),
        )

    async def _async_update_data(self):
        """Fetch data from API."""
        if not await self.api.update():
            raise UpdateFailed("Error communicating with API")

        return {
            "live": self.api.live_stations,
            "forecast": self.api.forecast,
        }
