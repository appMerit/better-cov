"""Data schemas for TravelOps Assistant."""

from typing import Any

from pydantic import BaseModel, Field


class Location(BaseModel):
    """Location information."""

    city: str
    country: str


class DateRange(BaseModel):
    """Date range for travel."""

    start_date: str  # YYYY-MM-DD format
    end_date: str  # YYYY-MM-DD format


class FlightInfo(BaseModel):
    """Flight information."""

    departure: str
    arrival: str
    date: str
    airline: str | None = None
    price: float | None = None


class HotelInfo(BaseModel):
    """Hotel information."""

    name: str
    location: str
    check_in: str
    check_out: str
    price_per_night: float | None = None


class Activity(BaseModel):
    """Activity information."""

    name: str
    location: str
    date: str | None = None
    description: str | None = None


class Itinerary(BaseModel):
    """Complete travel itinerary."""

    destination: Location
    dates: DateRange
    flights: list[FlightInfo] = Field(default_factory=list)
    hotels: list[HotelInfo] = Field(default_factory=list)
    activities: list[Activity] = Field(default_factory=list)
    budget: float | None = None
    notes: str | None = None


class TravelOpsResponse(BaseModel):
    """Response from TravelOps Assistant."""

    assistant_message: str
    itinerary: dict[str, Any]  # Will be validated against Itinerary schema
    session_id: str
