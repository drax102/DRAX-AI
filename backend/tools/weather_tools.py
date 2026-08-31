"""
weather_tools.py — Global weather and forecast tool using Open-Meteo free public API.
Requires no API key, works for any city worldwide.
"""

import requests
from backend.agent.tool_registry import register_tool
from backend.core.logger import get_logger

logger = get_logger(__name__)

WEATHER_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Foggy",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    95: "Thunderstorm",
}


def _geocode_city(city: str) -> tuple[float, float, str] | None:
    """Resolve city name to (lat, lon, resolved_name)."""
    try:
        url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=en&format=json"
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            results = resp.json().get("results")
            if results:
                r = results[0]
                return r["latitude"], r["longitude"], f"{r['name']}, {r.get('country', '')}"
    except Exception as e:
        logger.error(f"Geocoding error for {city}: {e}")
    return None


@register_tool(
    name="get_weather",
    description="Get current weather, temperature, humidity, and condition for any city.",
    parameters={"city": {"type": "string", "description": "City name (e.g. Delhi, Mumbai, London, New York, Jalandhar)", "default": "Delhi"}},
    risk_level="low",
    category="weather",
)
def get_weather(city: str = "Delhi") -> str:
    clean_city = city.strip()
    for w in ["weather in ", "weather for ", "temperature in ", "what is the weather in "]:
        if clean_city.lower().startswith(w):
            clean_city = clean_city[len(w):].strip()

    loc = _geocode_city(clean_city)
    if not loc:
        return f"Could not find location for '{city}'."

    lat, lon, place_name = loc
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m"
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()["current"]
            temp = data["temperature_2m"]
            humidity = data["relative_humidity_2m"]
            wind = data["wind_speed_10m"]
            code = data.get("weather_code", 0)
            condition = WEATHER_CODES.get(code, "Clear")

            return (
                f"Weather in {place_name}: {condition}, Temperature is {temp} C "
                f"with {humidity}% humidity and wind speed of {wind} km/h."
            )
    except Exception as e:
        logger.error(f"Weather fetch failed: {e}")

    return f"Unable to fetch current weather for {city} right now."
