"""Aircraft data sources: local dump1090/readsb, the airplanes.live API,
or a built-in demo simulator."""

import json
import time
import urllib.request

from .geo import dest_point

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


class DemoSource:
    """Synthetic traffic for demos and offline development: a small fleet
    flying straight tracks back and forth across the station circle."""

    name = "demo"

    # callsign, type, category, alt_ft, gs_kt, track_deg, vr_fpm, squawk
    _FLEET = [
        ("BAW117", "B77W", "A5", 37000, 480, 95, 0, "5523"),
        ("EZY45KL", "A320", "A3", 11000, 290, 212, -1100, "4612"),
        ("RYR8WC", "B738", "A3", 24500, 410, 331, 0, "7331"),
        ("DLH2XA", "A359", "A5", 8000, 255, 142, 1400, "1000"),
        ("N172SP", "C172", "A1", 2500, 105, 18, 0, "7000"),
        ("VIR300", "A35K", "A5", 39000, 495, 73, 0, "2200"),
    ]

    def __init__(self, lat, lon, radius_km, now=None):
        self.lat, self.lon, self.radius_km = lat, lon, radius_km
        self.t0 = time.time() if now is None else now

    def fetch(self, now=None):
        elapsed = (time.time() if now is None else now) - self.t0
        n = len(self._FLEET)
        crossing_km = 2.2 * self.radius_km
        out = []
        for i, (cs, typ, cat, alt, gs, trk, vr, sq) in enumerate(self._FLEET):
            speed_kmh = gs * KM_PER_NM  # 1 kt = 1 nm/h
            # along-track position, staggered per flight, wrapping each pass
            along = (elapsed / 3600.0 * speed_kmh
                     + i * crossing_km / n) % crossing_km - crossing_km / 2.0
            # offset each flight onto its own parallel chord
            offset = (i - (n - 1) / 2.0) * self.radius_km / 4.0
            lat, lon = dest_point(self.lat, self.lon, trk + 90.0, offset)
            lat, lon = dest_point(lat, lon, trk, along)
            out.append({
                "hex": "ade{:03d}".format(i),
                "callsign": cs,
                "lat": lat,
                "lon": lon,
                "alt_ft": alt,
                "gs_kt": float(gs),
                "track_deg": float(trk),
                "vr_fpm": float(vr),
                "squawk": sq,
                "type": typ,
                "category": cat,
            })
        return out
