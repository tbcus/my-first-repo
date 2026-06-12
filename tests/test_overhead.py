"""Unit tests for the overhead tracker backend (no network access)."""

import unittest

from overhead.config import Config
from overhead.geo import bearing_deg, haversine_km
from overhead.sources import DemoSource, Dump1090Source
from overhead.tracker import Tracker

LONDON = (51.5074, -0.1278)
PARIS = (48.8566, 2.3522)


class GeoTests(unittest.TestCase):
    def test_haversine_zero(self):
        self.assertAlmostEqual(haversine_km(*LONDON, *LONDON), 0.0, places=6)

    def test_haversine_london_paris(self):
        d = haversine_km(*LONDON, *PARIS)
        self.assertAlmostEqual(d, 344.0, delta=2.0)

    def test_bearing_due_north(self):
        self.assertAlmostEqual(bearing_deg(0.0, 0.0, 1.0, 0.0), 0.0, places=6)

    def test_bearing_due_east(self):
        self.assertAlmostEqual(bearing_deg(0.0, 0.0, 0.0, 1.0), 90.0, places=6)

    def test_bearing_due_south(self):
        self.assertAlmostEqual(bearing_deg(0.0, 0.0, -1.0, 0.0), 180.0, places=6)

    def test_bearing_due_west(self):
        self.assertAlmostEqual(bearing_deg(0.0, 0.0, 0.0, -1.0), 270.0, places=6)

    def test_bearing_range(self):
        b = bearing_deg(*LONDON, *PARIS)
        self.assertGreaterEqual(b, 0.0)
        self.assertLess(b, 360.0)


CANNED_DUMP1090 = {
    "now": 1700000000.0,
    "aircraft": [
        {  # good aircraft
            "hex": "ABC123", "flight": "BAW123  ", "lat": 51.5, "lon": -0.4,
            "alt_baro": 12000, "gs": 250.5, "track": 90.0, "baro_rate": -640,
            "squawk": "7000", "category": "A3", "seen": 0.1, "seen_pos": 0.5,
        },
        {  # no position -> skipped
            "hex": "def456", "flight": "EZY77", "alt_baro": 30000,
            "seen": 1.0,
        },
        {  # stale position -> skipped
            "hex": "aaa111", "flight": "RYR1", "lat": 51.0, "lon": 0.0,
            "alt_baro": 5000, "seen": 40.0, "seen_pos": 45.0,
        },
        {  # on the ground -> alt_ft 0
            "hex": "bbb222", "lat": 51.47, "lon": -0.45,
            "alt_baro": "ground", "seen_pos": 1.0,
        },
    ],
}


class Dump1090NormalizeTests(unittest.TestCase):
    def test_normalize(self):
        out = Dump1090Source._normalize(CANNED_DUMP1090)
        self.assertEqual(len(out), 2)
        ac = out[0]
        self.assertEqual(ac["hex"], "abc123")
        self.assertEqual(ac["callsign"], "BAW123")
        self.assertEqual(ac["lat"], 51.5)
        self.assertEqual(ac["lon"], -0.4)
        self.assertEqual(ac["alt_ft"], 12000)
        self.assertEqual(ac["gs_kt"], 250.5)
        self.assertEqual(ac["track_deg"], 90.0)
        self.assertEqual(ac["vr_fpm"], -640.0)
        self.assertEqual(ac["squawk"], "7000")
        self.assertEqual(ac["type"], "")
        self.assertEqual(ac["category"], "A3")

    def test_normalize_ground(self):
        out = Dump1090Source._normalize(CANNED_DUMP1090)
        ground = out[1]
        self.assertEqual(ground["hex"], "bbb222")
        self.assertEqual(ground["alt_ft"], 0)
        self.assertEqual(ground["callsign"], "")

    def test_normalize_empty(self):
        self.assertEqual(Dump1090Source._normalize({"aircraft": []}), [])
        self.assertEqual(Dump1090Source._normalize({}), [])


class DemoSourceTests(unittest.TestCase):
    def test_fleet_normalized_and_moving(self):
        src = DemoSource(51.47, -0.4543, 60.0, now=0.0)
        first = src.fetch(now=0.0)
        later = src.fetch(now=30.0)
        self.assertEqual(len(first), 6)
        for ac in first:
            for key in ("hex", "callsign", "lat", "lon", "alt_ft", "gs_kt",
                        "track_deg", "vr_fpm", "squawk", "type", "category"):
                self.assertIn(key, ac)
        # positions advance over time and stay near the station circle
        moved = haversine_km(first[0]["lat"], first[0]["lon"],
                             later[0]["lat"], later[0]["lon"])
        self.assertGreater(moved, 1.0)
        # flights spawn just outside the circle and fly through it
        for ac in first:
            self.assertLess(haversine_km(51.47, -0.4543, ac["lat"], ac["lon"]),
                            1.3 * 60.0)


class FakeSource:
    name = "fake"

    def __init__(self):
        self.aircraft = []
        self.fail = False

    def fetch(self):
        if self.fail:
            raise RuntimeError("boom")
        return [dict(a) for a in self.aircraft]


def make_aircraft(hexid="abc123", lat=51.5, lon=-0.4, alt_ft=10000, **kw):
    ac = {"hex": hexid, "callsign": "TEST1", "lat": lat, "lon": lon,
          "alt_ft": alt_ft, "gs_kt": 200.0, "track_deg": 45.0,
          "vr_fpm": 0.0, "squawk": "7000", "type": "B738", "category": "A3"}
    ac.update(kw)
    return ac


class TrackerTests(unittest.TestCase):
    def setUp(self):
        self.cfg = Config(lat=51.47, lon=-0.4543, radius_km=60.0,
                          trail_len=5)
        self.src = FakeSource()
        self.tracker = Tracker(self.cfg, source=self.src)

    def test_basic_update_and_snapshot(self):
        self.src.aircraft = [make_aircraft()]
        self.tracker.poll_once(now=1000.0)
        snap = self.tracker.snapshot()
        self.assertEqual(snap["source"], "fake")
        self.assertEqual(snap["station"],
                         {"lat": 51.47, "lon": -0.4543, "radius_km": 60.0})
        self.assertEqual(len(snap["aircraft"]), 1)
        ac = snap["aircraft"][0]
        self.assertEqual(ac["hex"], "abc123")
        self.assertEqual(ac["callsign"], "TEST1")
        self.assertIsInstance(ac["distance_km"], float)
        self.assertIsInstance(ac["bearing_deg"], int)
        self.assertTrue(0 <= ac["bearing_deg"] < 360)
        self.assertEqual(ac["trail"], [[51.5, -0.4, 10000]])

    def test_trail_appends_only_on_position_change(self):
        self.src.aircraft = [make_aircraft(lat=51.5, lon=-0.4)]
        self.tracker.poll_once(now=1000.0)
        self.tracker.poll_once(now=1001.0)  # same position
        self.src.aircraft = [make_aircraft(lat=51.51, lon=-0.41)]
        self.tracker.poll_once(now=1002.0)
        snap = self.tracker.snapshot()
        trail = snap["aircraft"][0]["trail"]
        self.assertEqual(trail, [[51.5, -0.4, 10000], [51.51, -0.41, 10000]])

    def test_trail_maxlen(self):
        for i in range(10):
            self.src.aircraft = [make_aircraft(lat=51.5 + i * 0.001)]
            self.tracker.poll_once(now=1000.0 + i)
        trail = self.tracker.snapshot()["aircraft"][0]["trail"]
        self.assertEqual(len(trail), 5)  # trail_len from config
        self.assertAlmostEqual(trail[-1][0], 51.509)

    def test_expiry_after_60s(self):
        self.src.aircraft = [make_aircraft()]
        self.tracker.poll_once(now=1000.0)
        self.src.aircraft = []
        self.tracker.poll_once(now=1059.0)
        self.assertEqual(len(self.tracker.snapshot()["aircraft"]), 1)
        self.tracker.poll_once(now=1061.0)
        self.assertEqual(len(self.tracker.snapshot()["aircraft"]), 0)

    def test_radius_filter(self):
        # ~111 km north of station, outside 60 km radius
        far = make_aircraft(hexid="far001", lat=52.47, lon=-0.4543)
        near = make_aircraft(hexid="near01", lat=51.5, lon=-0.45)
        self.src.aircraft = [far, near]
        self.tracker.poll_once(now=1000.0)
        snap = self.tracker.snapshot()
        hexes = [a["hex"] for a in snap["aircraft"]]
        self.assertEqual(hexes, ["near01"])

    def test_sorted_by_distance(self):
        self.src.aircraft = [
            make_aircraft(hexid="b", lat=51.6, lon=-0.45),
            make_aircraft(hexid="a", lat=51.48, lon=-0.45),
        ]
        self.tracker.poll_once(now=1000.0)
        snap = self.tracker.snapshot()
        dists = [a["distance_km"] for a in snap["aircraft"]]
        self.assertEqual(dists, sorted(dists))
        self.assertEqual(snap["aircraft"][0]["hex"], "a")

    def test_fetch_failure_propagates_from_poll_once(self):
        self.src.aircraft = [make_aircraft()]
        self.tracker.poll_once(now=1000.0)
        self.src.fail = True
        with self.assertRaises(RuntimeError):
            self.tracker.poll_once(now=1001.0)
        # last good state retained
        self.assertEqual(len(self.tracker.snapshot()["aircraft"]), 1)

    def test_poll_interval_from_config(self):
        cfg = Config(poll_s=1.0)
        src = FakeSource()
        src.name = "dump1090"
        t = Tracker(cfg, source=src)
        self.assertEqual(t.poll_s, 1.0)


if __name__ == "__main__":
    unittest.main()
