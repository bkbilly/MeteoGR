"""Sensor platform for Meteo.gr."""

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, CONF_STATION_NAME, DOMAIN
from .coordinator import MeteoGrDataUpdateCoordinator

SENSOR_TYPES: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key="temperature",
        name="Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="humidity",
        name="Humidity",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="pressure",
        name="Pressure",
        native_unit_of_measurement=UnitOfPressure.HPA,
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:gauge",
    ),
    SensorEntityDescription(
        key="wind_kmh",
        name="Wind Speed",
        native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
        device_class=SensorDeviceClass.WIND_SPEED,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:weather-windy",
    ),
    SensorEntityDescription(
        key="wind_bf",
        name="Wind Beaufort",
        native_unit_of_measurement="Bft",
        icon="mdi:weather-windy-variant",
    ),
    SensorEntityDescription(
        key="wind_dir",
        name="Wind Direction",
        icon="mdi:compass-outline",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    station_name = entry.data[CONF_STATION_NAME]

    entities = [
        MeteoGrSensor(coordinator, description, station_name)
        for description in SENSOR_TYPES
    ]
    async_add_entities(entities)


class MeteoGrSensor(CoordinatorEntity[MeteoGrDataUpdateCoordinator], SensorEntity):
    """Implementation of a Meteo.gr sensor."""

    _attr_attribution = ATTRIBUTION

    def __init__(
        self,
        coordinator: MeteoGrDataUpdateCoordinator,
        description: SensorEntityDescription,
        station_name: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._station_name = station_name
        self._attr_unique_id = (
            f"{coordinator.api.city_id}_{station_name}_{description.key}"
        )
        self._attr_name = f"{station_name} {description.name}"
        # You can create a device so all sensors are grouped
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{coordinator.api.city_id}_{station_name}")},
            "name": f"Meteo.gr {station_name}",
            "manufacturer": "Meteo.gr",
            "entry_type": "service",
        }

    @property
    def native_value(self):
        """Return the state of the sensor."""
        for station in self.coordinator.data["live"]:
            if station["name"] == self._station_name:
                return station.get(self.entity_description.key)
        return None
