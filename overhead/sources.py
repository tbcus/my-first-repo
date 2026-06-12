"""Aircraft data sources: local dump1090/readsb or the airplanes.live API."""

import json
import urllib.request

USER_AGENT = "overhead-tracker/1.0"
HTTP_TIMEOUT_S = 10
MAX_RADIUS_NM = 250.0
KM_PER_NM = 1.852
DUMP1090_MAX_SEEN_POS_S = 30.0


def _http_get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_S) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _to_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _alt_ft(value):
    """Altitude in feet as int; 'ground', missing or junk -> 0."""
    if value is None or value == "ground":
        return 0
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return 0


def _normalize_one(ac):
    """Normalize one raw aircraft record (shared field names across sources)."""
    return {
        "hex": str(ac.get("hex", "")).strip().lower(),
        "callsign": str(ac.get("flight") or "").strip(),
        "lat": float(ac["lat"]),
        "lon": float(ac["lon"]),
        "alt_ft": _alt_ft(ac.get("alt_baro")),
        "gs_kt": _to_float(ac.get("gs")),
        "track_deg": _to_float(ac.get("track")),
        "vr_fpm": _to_float(ac.get("baro_rate")),
        "squawk": str(ac.get("squawk") or ""),
        "type": str(ac.get("t") or ""),
        "category": str(ac.get("category") or ""),
    }


class Dump1090Source:
    """Reads aircraft.json from a local dump1090/readsb instance."""

    name = "dump1090"

    def __init__(self, url):
        self.url = url

    def fetch(self):
        return self._normalize(_http_get_json(self.url))

    @staticmethod
    def _normalize(raw):
        out = []
        for ac in raw.get("aircraft", []):
            if ac.get("lat") is None or ac.get("lon") is None:
                continue
            seen_pos = ac.get("seen_pos")
            if seen_pos is not None and _to_float(seen_pos) > DUMP1090_MAX_SEEN_POS_S:
                continue
            out.append(_normalize_one(ac))
        return out


class ApiSource:
    """Reads from the free, no-key airplanes.live point API."""

    name = "api"

    def __init__(self, lat, lon, radius_km):
        radius_nm = min(radius_km / KM_PER_NM, MAX_RADIUS_NM)
        self.url = "https://api.airplanes.live/v2/point/{}/{}/{}".format(
            lat, lon, radius_nm)

    def fetch(self):
        return self._normalize(_http_get_json(self.url))

    @staticmethod
    def _normalize(raw):
        out = []
        for ac in raw.get("ac", []) or []:
            if ac.get("lat") is None or ac.get("lon") is None:
                continue
            out.append(_normalize_one(ac))
        return out
