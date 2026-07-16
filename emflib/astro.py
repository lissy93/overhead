from math import sin, cos, sqrt, atan2, radians, degrees

_A = 6378137.0              # WGS84 semi-major axis, m
_E2 = 0.00669437999014      # WGS84 first eccentricity squared
_R = 6371.0088              # mean Earth radius, km

_POINTS = ("N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
           "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW")


def haversine_km(lat1, lon1, lat2, lon2):
    p1, p2 = radians(lat1), radians(lat2)
    dphi = radians(lat2 - lat1)
    dlam = radians(lon2 - lon1)
    a = sin(dphi / 2) ** 2 + cos(p1) * cos(p2) * sin(dlam / 2) ** 2
    return _R * 2 * atan2(sqrt(a), sqrt(1 - a))


def _ecef(lat, lon, h):
    la, lo = radians(lat), radians(lon)
    n = _A / sqrt(1 - _E2 * sin(la) ** 2)
    return ((n + h) * cos(la) * cos(lo),
            (n + h) * cos(la) * sin(lo),
            (n * (1 - _E2) + h) * sin(la))


def look_angles(obs, lat, lon, alt_km):
    """Azimuth, elevation (deg) and slant range (km) of a target from obs."""
    xo, yo, zo = _ecef(obs["lat"], obs["lon"], obs["elev"])
    xs, ys, zs = _ecef(lat, lon, alt_km * 1000.0)
    dx, dy, dz = xs - xo, ys - yo, zs - zo
    la, lo = radians(obs["lat"]), radians(obs["lon"])
    east = -sin(lo) * dx + cos(lo) * dy
    north = -sin(la) * cos(lo) * dx - sin(la) * sin(lo) * dy + cos(la) * dz
    up = cos(la) * cos(lo) * dx + cos(la) * sin(lo) * dy + sin(la) * dz
    az = (degrees(atan2(east, north)) + 360.0) % 360.0
    el = degrees(atan2(up, sqrt(east * east + north * north)))
    return az, el, sqrt(dx * dx + dy * dy + dz * dz) / 1000.0


def compass_point(az):
    return _POINTS[int((az % 360) / 22.5 + 0.5) % 16]
