"""API client for fetching weather data from meteo.gr."""

from datetime import date, datetime
import logging
import re

import aiohttp
from bs4 import BeautifulSoup, NavigableString

_LOGGER = logging.getLogger(__name__)


class MeteoGrScraper:
    """A class to fetch and parse weather data from meteo.gr."""

    BASE_URL = "https://meteo.gr/cf-en.cfm?city_id={city_id}"

    def __init__(self, session: aiohttp.ClientSession, city_id: int) -> None:
        """Initialize the scraper."""
        self.session = session
        self.city_id = city_id
        self.url = self.BASE_URL.format(city_id=self.city_id)
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"
        }
        self.live_stations = []
        self.forecast = []

    async def _fetch_soup(self):
        """Fetch content and return a BeautifulSoup object."""
        try:
            async with self.session.get(self.url, headers=self.headers) as response:
                response.raise_for_status()
                html = await response.text()
                return BeautifulSoup(html, "html.parser")
        except aiohttp.ClientError as err:
            _LOGGER.error("Error fetching data from meteo.gr: %s", err)
            return None

    def _clean_value(self, value, value_type=int):
        """Extract a number from a string and convert it."""
        if value is None:
            return None
        match = re.search(r"[-+]?\d*\.\d+|[-+]?\d+", str(value))
        if match:
            try:
                return value_type(float(match.group()))
            except (ValueError, TypeError):
                return None
        return None

    def _parse_live_stations(self, soup: BeautifulSoup):
        """Parse live station data."""
        live_container = soup.find("div", id="live")
        if not live_container:
            return []

        station_names_divs = live_container.select(".nowHead2")
        station_panels = live_container.select(".nowpanel")

        stations_data = []
        for name_div, panel_div in zip(station_names_divs, station_panels, strict=False):
            if name_div is None:
                continue
            try:
                station_name = name_div.find(string=True, recursive=False).strip()
                temp_tag = panel_div.select_one(".nowtemp")
                humid_tags = panel_div.find_all("div", {"class": "humid"})
                if humid_tags is None:
                    continue
                temperature = None
                if temp_tag:
                    temperature = temp_tag.get_text()
                humidity = None
                if len(humid_tags) > 0:
                    if len(humid_tags[0].contents) > 1:
                        humidity = humid_tags[0].contents[1]
                pressure = None
                if len(humid_tags) > 1:
                    if len(humid_tags[1].contents) > 1:
                        pressure = humid_tags[1].contents[1]
                wind_kmh = None
                if panel_div.select_one(".windnumber"):
                    wind_kmh = panel_div.select_one(".windnumber").get_text()
                wind_bf = None
                if panel_div.select_one(".nowbeaufort"):
                    wind_bf = panel_div.select_one(".nowbeaufort").get_text()
                wind_dir = None
                if panel_div.select_one(".winddirection"):
                    wind_dir = panel_div.select_one(".winddirection").get_text(strip=True)
                stations_data.append(
                    {
                        "name": station_name,
                        "temperature": self._clean_value(temperature, float),
                        "humidity": self._clean_value(humidity,int),
                        "pressure": self._clean_value(pressure, float),
                        "wind_kmh": self._clean_value(wind_kmh, float),
                        "wind_bf": self._clean_value(wind_bf, int),
                        "wind_dir": wind_dir,
                    }
                )
            except (AttributeError, IndexError) as e:
                _LOGGER.warning("Skipping a station due to parsing error: %s", e)
                continue
        return stations_data

    def _parse_forecast(self, soup: BeautifulSoup):
        # Remove Dust
        elements = soup.find_all("div", id="dust")
        for element in elements:
            element.decompose()

        stations_data = []
        day = ""
        month = ""
        time = ""
        temperature = ""
        humidity = ""
        wind_kmh = ""
        wind_dir = ""
        wind_bf = ""
        prediction = ""
        month_map = {
            name: num
            for num, name in enumerate(
                [
                    "January",
                    "February",
                    "March",
                    "April",
                    "May",
                    "June",
                    "July",
                    "August",
                    "September",
                    "October",
                    "November",
                    "December",
                ],
                1,
            )
        }
        for prognosis in soup.select("table[id^=outerTable]:not(.hidden-xs)"):
            for table in prognosis.find_all("tr"):
                day_find = table.find("td", {"class": "forecastDate"})
                if day_find is not None:
                    day = int(
                        day_find.find("span", {"class": "dayNumbercf"})
                        .contents[0]
                        .strip()
                    )
                    month = month_map.get(
                        day_find.find("span", {"class": "monthNumbercf"})
                        .get_text()
                        .strip()
                    )
                    today = date.today()
                    current_year = today.year
                    forecast_year = (
                        current_year + 1 if month < today.month else current_year
                    )

                if "perhour" in str(table.get("class")):
                    try:
                        time = table.find("table").get_text().strip()
                        hour, minute = map(int, time.split(":"))
                        forecast_datetime = datetime(
                            forecast_year, month, day, hour, minute
                        )
                    except:
                        continue
                    humidity_find = table.find("td", {"class": "humidity"})
                    temperature_find = table.find("td", {"class": "temperature"})
                    wind_find = table.find("td", {"class": "anemosfull"})
                    prediction_find = table.find("td", {"class": "phenomeno-name"})
                    if temperature_find is not None and len(temperature_find.contents) > 0:
                        if isinstance(temperature_find.contents[0], NavigableString):
                            temperature = temperature_find.contents[0].strip()
                        if len(temperature_find.contents) > 1 and isinstance(temperature_find.contents[1], NavigableString):
                            temperature = temperature_find.contents[1].strip()
                    if humidity_find is not None and len(humidity_find.contents) > 0:
                        humidity = humidity_find.contents[0].strip()
                    if wind_find is not None:
                        wind_bf = "0"
                        wind_dir = ""
                        wind_kmh = "0"
                        if wind_find.td.span is not None:
                            if len(wind_find.td.span.contents) > 0:
                                wind_kmh, _ = wind_find.td.span.contents[0].strip().split()
                            wind_bf, _, wind_dir = (
                                wind_find.td.contents[0].strip().split()
                            )
                    prediction_find = table.find("td", {"class": "phenomeno-name"})
                    if prediction_find is not None:
                        prediction = ""
                        if len(prediction_find.contents) > 0:
                            prediction = prediction_find.contents[0].strip()
                        stations_data.append(
                            {
                                "datetime": forecast_datetime.isoformat(),
                                "temperature": self._clean_value(temperature),
                                "humidity": self._clean_value(humidity),
                                "wind_kmh": self._clean_value(wind_kmh),
                                "wind_bf": self._clean_value(wind_bf),
                                "wind_dir": wind_dir,
                                "prediction": prediction,
                            }
                        )
        return stations_data

    async def update(self):
        """Fetch and parse all data."""
        soup = await self._fetch_soup()
        if soup:
            self.live_stations = self._parse_live_stations(soup)
            self.forecast = self._parse_forecast(soup)
            return True
        return False

# if __name__ == "__main__":
#     import asyncio

#     async def main():
#         async with aiohttp.ClientSession() as session:
#             scraper = MeteoGrScraper(session, city_id=88)
#             success = await scraper.update()
#             if success:
#                 print("Live Stations:", scraper.live_stations)
#                 print("Forecast:", scraper.forecast)
#             else:
#                 print("Failed to fetch data.")

#     asyncio.run(main())
