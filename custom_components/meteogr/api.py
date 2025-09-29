"""API client for fetching weather data from meteo.gr."""

from datetime import date, datetime
import logging
import re

import aiohttp
from bs4 import BeautifulSoup

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
            async with self.session.get(
                self.url, headers=self.headers, timeout=15
            ) as response:
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
        for name_div, panel_div in zip(
            station_names_divs, station_panels, strict=False
        ):
            try:
                station_name = name_div.find(string=True, recursive=False).strip()
                temp_tag = panel_div.select_one(".nowtemp")
                humid_tags = panel_div.find_all("div", {"class": "humid"})

                stations_data.append(
                    {
                        "name": station_name,
                        "temperature": self._clean_value(
                            temp_tag.get_text() if temp_tag else None, float
                        ),
                        "humidity": self._clean_value(
                            humid_tags[0].contents[1] if len(humid_tags) > 0 else None,
                            int,
                        ),
                        "pressure": self._clean_value(
                            humid_tags[1].contents[1] if len(humid_tags) > 1 else None,
                            float,
                        ),
                        "wind_kmh": self._clean_value(
                            panel_div.select_one(".windnumber").get_text()
                            if panel_div.select_one(".windnumber")
                            else None,
                            float,
                        ),
                        "wind_bf": self._clean_value(
                            panel_div.select_one(".nowbeaufort").get_text()
                            if panel_div.select_one(".nowbeaufort")
                            else None,
                            int,
                        ),
                        "wind_dir": panel_div.select_one(".winddirection").get_text(
                            strip=True
                        )
                        if panel_div.select_one(".winddirection")
                        else None,
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
                    temperature_find_1 = table.find("td", {"class": "temperature"})
                    temperature_find_2 = table.find("div", {"class": "tempcolorcell"})
                    wind_find = table.find("td", {"class": "anemosfull"})
                    prediction_find = table.find("td", {"class": "phenomeno-name"})
                    if temperature_find_1 is not None:
                        temperature = temperature_find_1.contents[0].strip()
                    if temperature_find_2 is not None:
                        temperature = temperature_find_2.contents[0].strip()
                    if humidity_find is not None:
                        humidity = humidity_find.contents[0].strip()
                    if wind_find is not None:
                        if wind_find.td.span is None:
                            wind_bf = "0"
                            wind_dir = ""
                            wind_kmh = "0"
                        else:
                            wind_kmh, _ = wind_find.td.span.contents[0].strip().split()
                            wind_bf, _, wind_dir = (
                                wind_find.td.contents[0].strip().split()
                            )
                    prediction_find = table.find("td", {"class": "phenomeno-name"})
                    if prediction_find is not None:
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

    def _parse_live_stations(self, soup: BeautifulSoup):
        """Parse live station data."""
        live_container = soup.find("div", id="live")
        if not live_container:
            return []

        station_names_divs = live_container.select(".nowHead2")
        station_panels = live_container.select(".nowpanel")

        stations_data = []
        for name_div, panel_div in zip(
            station_names_divs, station_panels, strict=False
        ):
            try:
                station_name = name_div.find(string=True, recursive=False).strip()
                temp_tag = panel_div.select_one(".nowtemp")
                humid_tags = panel_div.find_all("div", {"class": "humid"})

                stations_data.append(
                    {
                        "name": station_name,
                        "temperature": self._clean_value(
                            temp_tag.get_text() if temp_tag else None, float
                        ),
                        "humidity": self._clean_value(
                            humid_tags[0].contents[1] if len(humid_tags) > 0 else None,
                            int,
                        ),
                        "pressure": self._clean_value(
                            humid_tags[1].contents[1] if len(humid_tags) > 1 else None,
                            float,
                        ),
                        "wind_kmh": self._clean_value(
                            panel_div.select_one(".windnumber").get_text()
                            if panel_div.select_one(".windnumber")
                            else None,
                            float,
                        ),
                        "wind_bf": self._clean_value(
                            panel_div.select_one(".nowbeaufort").get_text()
                            if panel_div.select_one(".nowbeaufort")
                            else None,
                            int,
                        ),
                        "wind_dir": panel_div.select_one(".winddirection").get_text(
                            strip=True
                        )
                        if panel_div.select_one(".winddirection")
                        else None,
                    }
                )
            except (AttributeError, IndexError) as e:
                _LOGGER.warning("Skipping a station due to parsing error: %s", e)
                continue
        return stations_data

    async def update(self):
        """Fetch and parse all data."""
        soup = await self._fetch_soup()
        if soup:
            self.live_stations = self._parse_live_stations(soup)
            self.forecast = self._parse_forecast(soup)
            return True
        return False
