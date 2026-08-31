"""
weather_tools.py — Global weather and forecast tool using Open-Meteo & wttr.in fallback.
Requires no API key, works for any city worldwide with high reliability.
"""

import urllib.parse
import requests
from backend.agent.tool_registry import register_tool
from backend.core.logger import get_logger

logger = get_logger(__name__)

# Standard browser/assistant headers to prevent cloud IP rate-limiting/blocking
REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 DRAX-AI/2.0",
    "Accept": "application/json",
}

# WMO Weather interpretation codes (WW)
WEATHER_CODES = {
    0: "Clear skies",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Foggy",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow fall",
    73: "Moderate snow fall",
    75: "Heavy snow fall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}

# Fallback coordinates for major world cities in case geocoding is temporarily slow or unavailable
MAJOR_CITIES_COORDS = {
    "delhi": (28.65195, 77.23149, "Delhi, India"),
    "new delhi": (28.6139, 77.2090, "New Delhi, India"),
    "mumbai": (19.0760, 72.8777, "Mumbai, India"),
    "chandigarh": (30.7333, 76.7794, "Chandigarh, India"),
    "jalandhar": (31.3260, 75.5762, "Jalandhar, India"),
    "bengaluru": (12.9716, 77.5946, "Bengaluru, India"),
    "bangalore": (12.9716, 77.5946, "Bengaluru, India"),
    "kolkata": (22.5726, 88.3639, "Kolkata, India"),
    "chennai": (13.0827, 80.2707, "Chennai, India"),
    "hyderabad": (17.3850, 78.4867, "Hyderabad, India"),
    "london": (51.5074, -0.1278, "London, United Kingdom"),
    "new york": (40.7128, -74.0060, "New York, United States"),
    "nyc": (40.7128, -74.0060, "New York, United States"),
    "san francisco": (37.7749, -122.4194, "San Francisco, United States"),
    "tokyo": (35.6762, 139.6503, "Tokyo, Japan"),
    "paris": (48.8566, 2.3522, "Paris, France"),
    "berlin": (52.5200, 13.4050, "Berlin, Germany"),
    "dubai": (25.2048, 55.2708, "Dubai, United Arab Emirates"),
    "toronto": (43.6532, -79.3832, "Toronto, Canada"),
    "sydney": (-33.8688, 151.2093, "Sydney, Australia"),
}


def _clean_city_name(city: str) -> str:
    """Clean and extract a pure city name from natural language inputs."""
    if not city:
        return "Delhi"
    clean = city.strip()
    prefixes = [
        "what is the weather in ",
        "what's the weather in ",
        "how is the weather in ",
        "check the weather in ",
        "show me the weather in ",
        "what is the temperature in ",
        "what's the temperature in ",
        "weather in ",
        "weather for ",
        "weather at ",
        "temperature in ",
        "temperature for ",
        "current weather in ",
        "current weather for ",
    ]
    for p in prefixes:
        if clean.lower().startswith(p):
            clean = clean[len(p):].strip()
            break
    clean = clean.strip(" ?.!,'\":;").strip()
    return clean or "Delhi"


def _geocode_city(city: str) -> tuple[float, float, str] | None:
    """Resolve city name to (lat, lon, resolved_name)."""
    # 1. Check quick coordinates cache
    city_key = city.lower().strip()
    if city_key in MAJOR_CITIES_COORDS:
        return MAJOR_CITIES_COORDS[city_key]

    # 2. Query Open-Meteo Geocoding API
    try:
        encoded = urllib.parse.quote(city)
        url = f"https://geocoding-api.open-meteo.com/v1/search?name={encoded}&count=1&language=en&format=json"
        resp = requests.get(url, headers=REQUEST_HEADERS, timeout=6)
        if resp.status_code == 200:
            results = resp.json().get("results")
            if results and len(results) > 0:
                r = results[0]
                country = r.get("country", "")
                name = r.get("name", city)
                display_name = f"{name}, {country}" if country else name
                return float(r["latitude"]), float(r["longitude"]), display_name
    except Exception as e:
        logger.warning(f"Open-Meteo geocoding error for {city}: {e}")

    return None


def _fetch_open_meteo(lat: float, lon: float, place_name: str) -> str | None:
    """Fetch live weather from Open-Meteo Forecast API."""
    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat}&longitude={lon}&"
            f"current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m"
        )
        resp = requests.get(url, headers=REQUEST_HEADERS, timeout=6)
        if resp.status_code == 200:
            data = resp.json().get("current")
            if data and "temperature_2m" in data:
                temp = round(float(data["temperature_2m"]), 1)
                humidity = data.get("relative_humidity_2m", 0)
                wind = round(float(data.get("wind_speed_10m", 0.0)), 1)
                code = int(data.get("weather_code", 0))
                condition = WEATHER_CODES.get(code, "Clear skies")

                return (
                    f"Weather in {place_name}: {condition}, Temperature is {temp}°C "
                    f"with {humidity}% humidity and wind speed of {wind} km/h."
                )
    except Exception as e:
        logger.warning(f"Open-Meteo forecast fetch failed for {place_name}: {e}")
    return None


def _fetch_wttr_fallback(city: str) -> str | None:
    """Fallback weather query via wttr.in public JSON API."""
    try:
        encoded = urllib.parse.quote(city)
        url = f"https://wttr.in/{encoded}?format=j1"
        resp = requests.get(url, headers=REQUEST_HEADERS, timeout=6)
        if resp.status_code == 200:
            data = resp.json()
            curr = data.get("current_condition", [{}])[0]
            area = data.get("nearest_area", [{}])[0]

            city_name = area.get("areaName", [{}])[0].get("value", city)
            country_name = area.get("country", [{}])[0].get("value", "")
            place_name = f"{city_name}, {country_name}" if country_name else city_name

            temp = curr.get("temp_C", "N/A")
            humidity = curr.get("humidity", "N/A")
            wind = curr.get("windspeedKmph", "N/A")
            desc = curr.get("weatherDesc", [{}])[0].get("value", "Clear")

            return (
                f"Weather in {place_name}: {desc}, Temperature is {temp}°C "
                f"with {humidity}% humidity and wind speed of {wind} km/h."
            )
    except Exception as e:
        logger.warning(f"wttr.in fallback failed for {city}: {e}")
    return None


@register_tool(
    name="get_weather",
    description="Get current weather, temperature, humidity, and condition for any city worldwide.",
    parameters={"city": {"type": "string", "description": "City name (e.g. Delhi, Mumbai, London, New York, Chandigarh, Jalandhar)", "default": "Delhi"}},
    risk_level="low",
    category="weather",
)
def get_weather(city: str = "Delhi") -> str:
    clean_city = _clean_city_name(city)

    # 1. Try Open-Meteo with geocoding
    loc = _geocode_city(clean_city)
    if loc:
        lat, lon, place_name = loc
        weather_report = _fetch_open_meteo(lat, lon, place_name)
        if weather_report:
            return weather_report

    # 2. Fallback to wttr.in
    wttr_report = _fetch_wttr_fallback(clean_city)
    if wttr_report:
        return wttr_report

    # 3. If geocoding failed and wttr failed, provide informative error
    if not loc:
        return f"Could not find location coordinates for '{clean_city}'. Please check the city spelling."

    return f"Weather service temporarily unavailable for '{clean_city}'. Please try again in a moment."
