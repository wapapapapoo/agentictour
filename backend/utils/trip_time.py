from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone, tzinfo
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

DEFAULT_TRIP_TIMEZONE = "Asia/Shanghai"


def resolve_trip_timezone(name: str | None) -> tzinfo:
    try:
        return ZoneInfo(name or DEFAULT_TRIP_TIMEZONE)
    except ZoneInfoNotFoundError:
        return timezone(timedelta(hours=8))


def utc_database_time_to_local(value: datetime, timezone_name: str | None) -> datetime:
    """Interpret a naive DB datetime as UTC and return an aware local value."""
    aware_utc = (
        value.replace(tzinfo=UTC)
        if value.tzinfo is None
        else value.astimezone(UTC)
    )
    return aware_utc.astimezone(resolve_trip_timezone(timezone_name))


def trip_local_iso(value: datetime, timezone_name: str | None) -> str:
    return utc_database_time_to_local(value, timezone_name).isoformat(
        timespec="minutes"
    )


def trip_time_context(timezone_name: str | None) -> dict[str, str]:
    resolved_name = timezone_name or DEFAULT_TRIP_TIMEZONE
    local_now = datetime.now(UTC).astimezone(resolve_trip_timezone(resolved_name))
    return {
        "timezone": resolved_name,
        "display_timezone": resolved_name,
        "database_timezone": "UTC",
        "current_time_local": local_now.isoformat(timespec="seconds"),
    }


def trip_route_context(origin_city: str, destination_city: str) -> dict[str, object]:
    """Expose route roles explicitly so current location cannot replace destination."""
    return {
        "route_context": {
            "departure_city": origin_city,
            "tourism_destination_city": destination_city,
            "cross_city": origin_city.strip() != destination_city.strip(),
        }
    }
