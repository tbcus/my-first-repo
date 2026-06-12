"""Configuration loaded from environment variables."""

import os
from dataclasses import dataclass

DEFAULT_LAT = 51.4700
DEFAULT_LON = -0.4543
DEFAULT_RADIUS_KM = 60.0
DEFAULT_PORT = 8000
DEFAULT_SOURCE = "dump1090"
DEFAULT_DUMP1090_URL = "http://127.0.0.1:8080/data/aircraft.json"
DEFAULT_POLL_S = 1.0
DEFAULT_TRAIL_LEN = 120


@dataclass
class Config:
    lat: float = DEFAULT_LAT
    lon: float = DEFAULT_LON
    radius_km: float = DEFAULT_RADIUS_KM
    port: int = DEFAULT_PORT
    source: str = DEFAULT_SOURCE  # "dump1090" | "demo"
    dump1090_url: str = DEFAULT_DUMP1090_URL
    poll_s: float = DEFAULT_POLL_S
    trail_len: int = DEFAULT_TRAIL_LEN


def _env(name, default, cast):
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        return cast(raw)
    except (TypeError, ValueError):
        return default


def load() -> Config:
    """Build a Config from OVERHEAD_* environment variables."""
    source = _env("OVERHEAD_SOURCE", DEFAULT_SOURCE, str).strip().lower()
    if source not in ("dump1090", "demo"):
        source = DEFAULT_SOURCE
    return Config(
        lat=_env("OVERHEAD_LAT", DEFAULT_LAT, float),
        lon=_env("OVERHEAD_LON", DEFAULT_LON, float),
        radius_km=_env("OVERHEAD_RADIUS_KM", DEFAULT_RADIUS_KM, float),
        port=_env("OVERHEAD_PORT", DEFAULT_PORT, int),
        source=source,
        dump1090_url=_env("OVERHEAD_DUMP1090_URL", DEFAULT_DUMP1090_URL, str),
        poll_s=_env("OVERHEAD_POLL_S", DEFAULT_POLL_S, float),
        trail_len=_env("OVERHEAD_TRAIL_LEN", DEFAULT_TRAIL_LEN, int),
    )
