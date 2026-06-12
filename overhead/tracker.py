"""Background tracker: polls a source and maintains per-aircraft state."""

import logging
import threading
import time
from collections import deque

from .geo import bearing_deg, haversine_km
from .sources import DemoSource, Dump1090Source

log = logging.getLogger(__name__)

EXPIRE_S = 60.0


class Tracker:
    """Polls an aircraft source and keeps a thread-safe state snapshot."""

    def __init__(self, config, source=None):
        self.config = config
        self.source = source if source is not None else self._choose_source(config)
        self.poll_s = config.poll_s
        self._lock = threading.Lock()
        self._state = {}  # hex -> aircraft record
        self._stop = threading.Event()
        self._thread = None

    @staticmethod
    def _choose_source(config):
        if config.source == "demo":
            return DemoSource(config.lat, config.lon, config.radius_km)
        return Dump1090Source(config.dump1090_url)

    # -- lifecycle -----------------------------------------------------

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True,
                                        name="overhead-tracker")
        self._thread.start()

    def stop(self):
        self._stop.set()

    def _run(self):
        while not self._stop.is_set():
            try:
                self.poll_once()
            except Exception:
                log.warning("poll failed; keeping last good state", exc_info=True)
            self._stop.wait(self.poll_s)

    # -- core update ---------------------------------------------------

    def poll_once(self, now=None):
        """Fetch once and merge into state. Raises on fetch failure."""
        now = time.time() if now is None else now
        aircraft = self.source.fetch()
        cfg = self.config
        with self._lock:
            for ac in aircraft:
                hexid = ac.get("hex")
                if not hexid:
                    continue
                dist = haversine_km(cfg.lat, cfg.lon, ac["lat"], ac["lon"])
                if dist > cfg.radius_km:
                    continue
                rec = self._state.get(hexid)
                if rec is None:
                    rec = {"trail": deque(maxlen=cfg.trail_len)}
                    self._state[hexid] = rec
                rec.update(ac)
                rec["distance_km"] = dist
                rec["bearing_deg"] = bearing_deg(cfg.lat, cfg.lon,
                                                 ac["lat"], ac["lon"])
                rec["last_seen"] = now
                point = (ac["lat"], ac["lon"], ac["alt_ft"])
                trail = rec["trail"]
                if not trail or (trail[-1][0], trail[-1][1]) != (point[0], point[1]):
                    trail.append(point)
            # drop stale aircraft
            for hexid in [h for h, r in self._state.items()
                          if now - r["last_seen"] > EXPIRE_S]:
                del self._state[hexid]

    # -- read side -----------------------------------------------------

    def snapshot(self):
        now = time.time()
        cfg = self.config
        with self._lock:
            aircraft = []
            for hexid, rec in self._state.items():
                aircraft.append({
                    "hex": hexid,
                    "callsign": rec.get("callsign", ""),
                    "lat": rec["lat"],
                    "lon": rec["lon"],
                    "alt_ft": rec.get("alt_ft", 0),
                    "gs_kt": rec.get("gs_kt", 0.0),
                    "track_deg": rec.get("track_deg", 0.0),
                    "vr_fpm": rec.get("vr_fpm", 0.0),
                    "squawk": rec.get("squawk", ""),
                    "type": rec.get("type", ""),
                    "category": rec.get("category", ""),
                    "distance_km": round(rec["distance_km"], 1),
                    "bearing_deg": int(round(rec["bearing_deg"])) % 360,
                    "seen_s": round(max(0.0, now - rec["last_seen"]), 1),
                    "trail": [[la, lo, al] for la, lo, al in rec["trail"]],
                })
        aircraft.sort(key=lambda a: a["distance_km"])
        return {
            "now": now,
            "source": getattr(self.source, "name", "unknown"),
            "station": {"lat": cfg.lat, "lon": cfg.lon,
                        "radius_km": cfg.radius_km},
            "aircraft": aircraft,
        }
