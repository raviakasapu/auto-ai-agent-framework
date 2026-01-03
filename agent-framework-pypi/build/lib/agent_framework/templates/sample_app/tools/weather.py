"""
Weather Lookup Tool - Mock weather information.

Demonstrates a read-only tool with simulated external API.
"""
from __future__ import annotations

import random
from typing import Dict, Any, Optional

from pydantic import BaseModel, Field

from agent_framework.base import BaseTool


class WeatherLookupArgs(BaseModel):
    """Arguments for weather lookup."""
    city: str = Field(..., description="City name to get weather for")
    units: str = Field("celsius", description="Temperature units: celsius or fahrenheit")


class WeatherLookupOutput(BaseModel):
    """Output from weather lookup."""
    city: str
    temperature: float
    units: str
    condition: str
    humidity: int
    wind_speed: float
    description: str


class WeatherLookupTool(BaseTool):
    """
    Mock weather lookup tool.

    Demonstrates:
    - Read-only external API simulation
    - Unit conversion
    - Structured output
    """

    _name = "weather_lookup"
    _description = "Get current weather information for a city. Returns temperature, conditions, humidity, and wind speed."

    # Mock weather data for demo
    _CONDITIONS = [
        ("sunny", "Clear skies with bright sunshine"),
        ("cloudy", "Overcast with gray clouds"),
        ("rainy", "Light rain showers"),
        ("partly_cloudy", "Mix of sun and clouds"),
        ("windy", "Strong winds with clear skies"),
    ]

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def args_schema(self):
        return WeatherLookupArgs

    @property
    def output_schema(self):
        return WeatherLookupOutput

    def execute(
        self,
        city: str,
        units: str = "celsius",
    ) -> Dict[str, Any]:
        """Get mock weather for a city."""
        # Generate consistent but varied mock data based on city name
        seed = sum(ord(c) for c in city.lower())
        random.seed(seed)

        # Generate temperature (10-35 C range)
        temp_celsius = random.uniform(10, 35)

        # Convert if needed
        if units.lower() == "fahrenheit":
            temperature = temp_celsius * 9/5 + 32
            unit_label = "fahrenheit"
        else:
            temperature = temp_celsius
            unit_label = "celsius"

        # Pick condition
        condition, desc = random.choice(self._CONDITIONS)

        # Generate other values
        humidity = random.randint(30, 90)
        wind_speed = random.uniform(0, 30)

        output = WeatherLookupOutput(
            city=city.title(),
            temperature=round(temperature, 1),
            units=unit_label,
            condition=condition,
            humidity=humidity,
            wind_speed=round(wind_speed, 1),
            description=f"{desc}. Temperature is {round(temperature, 1)}{'F' if unit_label == 'fahrenheit' else 'C'} with {humidity}% humidity.",
        )
        return output.model_dump()
