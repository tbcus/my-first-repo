"""Pure great-circle geometry helpers."""

import math

EARTH_RADIUS_KM = 6371.0088


def haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance in kilometres between two lat/lon points."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = (math.sin(dphi / 2.0) ** 2
         + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2.0) ** 2)
    return 2.0 * EARTH_RADIUS_KM * math.asin(min(1.0, math.sqrt(a)))


def dest_point(lat, lon, bearing, dist_km):
    """Destination lat/lon after travelling dist_km on an initial bearing."""
    phi1 = math.radians(lat)
    lam1 = math.radians(lon)
    theta = math.radians(bearing)
    delta = dist_km / EARTH_RADIUS_KM
    phi2 = math.asin(math.sin(phi1) * math.cos(delta)
                     + math.cos(phi1) * math.sin(delta) * math.cos(theta))
    lam2 = lam1 + math.atan2(
        math.sin(theta) * math.sin(delta) * math.cos(phi1),
        math.cos(delta) - math.sin(phi1) * math.sin(phi2))
    return math.degrees(phi2), (math.degrees(lam2) + 540.0) % 360.0 - 180.0


def bearing_deg(lat1, lon1, lat2, lon2):
    """Initial bearing from point 1 to point 2, degrees 0-360, 0 = north."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dlam = math.radians(lon2 - lon1)
    y = math.sin(dlam) * math.cos(phi2)
    x = (math.cos(phi1) * math.sin(phi2)
         - math.sin(phi1) * math.cos(phi2) * math.cos(dlam))
    return (math.degrees(math.atan2(y, x)) + 360.0) % 360.0
