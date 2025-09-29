"""Weather platform for Meteo.gr."""

from collections import Counter
from datetime import datetime
from itertools import groupby

from homeassistant.components.weather import (
    Forecast,
    WeatherEntity,
    WeatherEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfPressure, UnitOfSpeed, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, CONF_STATION_NAME, DOMAIN
from .coordinator import MeteoGrDataUpdateCoordinator

# Map meteo.gr condition names to HA condition names
CONDITION_MAP = {
    "Clear": "sunny",
    "Few Clouds": "partlycloudy",
    "Partly Cloudy": "partlycloudy",
    "Cloudy": "cloudy",
    "Thin Clouds": "cloudy",
    "Light Rain": "rainy",
    "Rain": "rainy",
    "Storm": "lightning-rainy",
    # Add other conditions as you find them
}
# This list determines which condition is chosen for the daily forecast.
# The first condition in this list that appears in a day's forecast will be used.
CONDITION_SEVERITY_ORDER = [
    "Storm",
    "Rain",
    "Light Rain",
    "Cloudy",
    "Partly Cloudy",
    "Thin Clouds",
    "Few Clouds",
    "Clear",
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the weather platform."""
    coordinator: MeteoGrDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][
        "coordinator"
    ]
    station_name = entry.data[CONF_STATION_NAME]
    async_add_entities([MeteoGrWeather(coordinator, station_name)])


class MeteoGrWeather(CoordinatorEntity[MeteoGrDataUpdateCoordinator], WeatherEntity):
    """Implementation of a Meteo.gr weather entity."""

    _attr_attribution = ATTRIBUTION
    _attr_native_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_native_pressure_unit = UnitOfPressure.HPA
    _attr_native_wind_speed_unit = UnitOfSpeed.KILOMETERS_PER_HOUR

    # MODIFICATION: Add FORECAST_DAILY to supported features
    _attr_supported_features = (
        WeatherEntityFeature.FORECAST_HOURLY | WeatherEntityFeature.FORECAST_DAILY
    )

    def __init__(
        self, coordinator: MeteoGrDataUpdateCoordinator, station_name: str
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._station_name = station_name
        self._attr_unique_id = f"{coordinator.api.city_id}_weather"
        self._attr_name = f"Meteo.gr {station_name}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{coordinator.api.city_id}_{station_name}")},
            "name": f"Meteo.gr {station_name}",
            "manufacturer": "Meteo.gr",
            "entry_type": "service",
        }
        # To hold the calculated daily forecast
        self._daily_forecast = []

    @property
    def condition(self) -> str | None:
        """Return the current condition."""
        if not self.coordinator.data or not self.coordinator.data["forecast"]:
            return None
        prediction = self.coordinator.data["forecast"][0].get("prediction")
        return CONDITION_MAP.get(prediction, "unknown")

    @property
    def native_temperature(self) -> float | None:
        """Return the temperature."""
        if not self.coordinator.data or not self.coordinator.data["forecast"]:
            return None
        return self.coordinator.data["forecast"][0].get("temperature")

    # NEW PROPERTY: Add native_templow for the current day
    @property
    def native_templow(self) -> float | None:
        """Return the low temperature of the current day."""
        if not self._daily_forecast:
            return None
        return self._daily_forecast[0].get("native_templow")

    @property
    def humidity(self) -> float | None:
        """Return the humidity."""
        if not self.coordinator.data or not self.coordinator.data["forecast"]:
            return None
        return self.coordinator.data["forecast"][0].get("humidity")

    @property
    def native_wind_speed(self) -> float | None:
        """Return the wind speed."""
        if not self.coordinator.data or not self.coordinator.data["forecast"]:
            return None
        return self.coordinator.data["forecast"][0].get("wind_kmh")

    @property
    def wind_bearing(self) -> str | None:
        """Return the wind bearing."""
        if not self.coordinator.data or not self.coordinator.data["forecast"]:
            return None
        return self.coordinator.data["forecast"][0].get("wind_dir")

    async def async_forecast_hourly(self) -> list[Forecast] | None:
        """Return the hourly forecast."""
        if not self.coordinator.data or not self.coordinator.data["forecast"]:
            return None

        forecasts = []
        for item in self.coordinator.data["forecast"]:
            myforecast = Forecast(
                datetime=item["datetime"],
                native_temperature=item["temperature"],
                native_wind_speed=item["wind_kmh"],
                wind_bearing=item["wind_dir"],
                condition=CONDITION_MAP.get(item["prediction"], "unknown"),
            )
            forecasts.append(myforecast)
        return forecasts

    async def async_forecast_daily(self) -> list[Forecast] | None:
        """Return the daily forecast."""
        if not self.coordinator.data or not self.coordinator.data["forecast"]:
            return None

        daily_forecasts = []
        # Group hourly forecasts by day
        for day, hourly_group in groupby(
            self.coordinator.data["forecast"],
            key=lambda f: datetime.fromisoformat(f["datetime"]).date(),
        ):
            hourly_items = list(hourly_group)

            # Extract temperatures, filtering out None values
            temps = [
                item["temperature"]
                for item in hourly_items
                if item["temperature"] is not None
            ]
            if not temps:
                continue  # Skip day if no temperature data

            # Find the most common condition and wind direction for the day
            conditions = [
                item["prediction"] for item in hourly_items if item["prediction"]
            ]
            worst_condition_for_day = None
            if conditions:
                # Iterate through our severity list (worst to best)
                for severity in CONDITION_SEVERITY_ORDER:
                    if severity in conditions:
                        worst_condition_for_day = severity
                        break  # Found the worst one, no need to check further

                # Fallback in case a new, unknown condition appears
                if not worst_condition_for_day:
                    worst_condition_for_day = conditions[0]

            wind_dirs = [item["wind_dir"] for item in hourly_items if item["wind_dir"]]

            most_common_wind_dir = (
                Counter(wind_dirs).most_common(1)[0][0] if wind_dirs else None
            )

            # Find max wind speed
            wind_speeds = [
                item["wind_kmh"]
                for item in hourly_items
                if item["wind_kmh"] is not None
            ]

            daily_forecasts.append(
                Forecast(
                    datetime=datetime.combine(day, datetime.min.time()).isoformat(),
                    native_temperature=max(temps),
                    native_templow=min(temps),
                    condition=CONDITION_MAP.get(worst_condition_for_day, "unknown"),
                    native_wind_speed=max(wind_speeds) if wind_speeds else None,
                    wind_bearing=most_common_wind_dir,
                )
            )

        self._daily_forecast = daily_forecasts  # Store for native_templow property
        return daily_forecasts
