# Meteo.gr Weather Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/bkbilly/meteogr.svg?style=flat-square)](https://github.com/bkbilly/meteogr/releases)
[![License](https://img.shields.io/github/license/bkbilly/meteogr.svg?style=flat-square)](LICENSE)
[![hacs](https://img.shields.io/badge/HACS-default-orange.svg?style=flat-square)](https://hacs.xyz)

This is a custom integration for Home Assistant that provides weather data from [Meteo.gr](https://meteo.gr), a popular weather service in Greece provided by the National Observatory of Athens.

This integration retrieves live data from nearby weather stations and provides a detailed hourly and daily forecast for a specified location (City ID). All configuration is handled through the user interface.


## Features

-   **Live Sensor Data:** Creates sensor entities for a user-selected local weather station (temperature, humidity, pressure, wind, etc.).
-   **Weather Forecast Entity:** Creates a `weather` entity with detailed hourly and daily forecasts.
-   **Smart Daily Forecast:** The daily forecast condition is based on the **worst** weather expected for that day (e.g., if it rains for one hour, the day's forecast will show "rainy").
-   **UI Configuration:** No YAML configuration required. Set up and configure everything from the Home Assistant frontend.
-   **Configurable Update Interval:** Choose how frequently you want to fetch new data.
-   **Device Grouping:** All sensors and the weather entity are grouped into a single device for your location, keeping your entity list clean.

## Installation

### HACS (Recommended)

HACS is the preferred way to install and manage this integration.

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=bkbilly&repository=meteogr&category=integration)

 - Find the "Meteo.gr" integration in the list and click "Install".
 - Restart Home Assistant.


## Configuration

Once installed, you can add the integration to Home Assistant.

1.  Navigate to **Settings** -> **Devices & Services**.
2.  Click the **+ Add Integration** button in the bottom right.
3.  Search for "Meteo.gr" and select it.
4.  You will be prompted for a **City ID**. To find your ID:
    -   Go to the [meteo.gr](https://meteo.gr) website.
    -   Search for your city or location.
    -   Look at the URL in your browser's address bar. It will look something like `https://meteo.gr/cf-en.cfm?city_id=88`.
    -   The number at the end is your **City ID**. In this example, it's `88`.
5.  The integration will validate the ID and then present a list of nearby live weather stations. Select the station you wish to use for your sensor data.
6.  Click **Submit**. The integration will be added, and a new device with all its entities will be created.

### Changing Options

After installation, you can change the update interval.

1.  Go to the Meteo.gr integration on the **Settings** -> **Devices & Services** page.
2.  Click the three-dots menu on the integration card and select **Configure**.
3.  Enter a new update interval in minutes and click **Submit**. The integration will automatically reload with the new setting.

## Entities Provided

This integration will create one device named `Meteo.gr {Station Name}` which includes the following entities:

| Platform | Entity ID                               | Description                                     |
| -------- | ----------------------------------------- | ----------------------------------------------- |
| `weather`  | `weather.meteogr_{station_name}`          | Full weather entity with hourly & daily forecast. |
| `sensor`   | `sensor.meteogr_{station_name}_temperature` | Current temperature (°C).                       |
| `sensor`   | `sensor.meteogr_{station_name}_humidity`    | Current humidity (%).                           |
| `sensor`   | `sensor.meteogr_{station_name}_pressure`    | Current barometric pressure (hPa).              |
| `sensor`   | `sensor.meteogr_{station_name}_wind_speed`  | Current wind speed (km/h).                      |
| `sensor`   | `sensor.meteogr_{station_name}_wind_beaufort` | Current wind force on the Beaufort scale.       |
| `sensor`   | `sensor.meteogr_{station_name}_wind_direction` | Current wind direction (e.g., N, SW, E).      |

*Note: `{station_name}` will be replaced by the name of the station you selected during configuration.*

---

## Attribution

-   All weather data is sourced from [meteo.gr](https://meteo.gr).
-   This is an unofficial integration and is not affiliated with or endorsed by the National Observatory of Athens / meteo.gr.
