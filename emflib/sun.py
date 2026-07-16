# Low-precision sun position, plenty good for "is it dark" and "is the ISS lit".
from math import sin, cos, asin, sqrt, radians, degrees

from .sgp4 import gmst

_RE = 6378.137  # earth radius in km, for the shadow test


def sun_vector(jd):
    n = jd - 2451545.0                                    # days since the J2000 epoch
    g = radians((357.528 + 0.9856003 * n) % 360.0)        # sun's mean anomaly
    lam = radians((280.460 + 0.9856474 * n) % 360.0) \
        + radians(1.915) * sin(g) + radians(0.020) * sin(2.0 * g)  # ecliptic longitude
    eps = radians(23.439 - 0.0000004 * n)                 # tilt of the earth
    # unit vector to the sun in the same inertial frame SGP4 hands us
    return (cos(lam), cos(eps) * sin(lam), sin(eps) * sin(lam))


def is_sunlit(r_eci, jd):
    sx, sy, sz = sun_vector(jd)
    proj = r_eci[0] * sx + r_eci[1] * sy + r_eci[2] * sz  # how far along the sun line it sits
    if proj > 0.0:
        return True                                       # sun side, always lit
    # behind earth: lit only if it pokes out past the shadow cylinder
    rmag2 = r_eci[0] ** 2 + r_eci[1] ** 2 + r_eci[2] ** 2
    perp = sqrt(rmag2 - proj * proj) if rmag2 > proj * proj else 0.0
    return perp > _RE


def altitude(lat, lon, jd):
    sx, sy, sz = sun_vector(jd)
    lst = gmst(jd) + radians(lon)                         # where the observer faces in space
    la = radians(lat)
    # observer's local up vector, then the sun's height above the horizon
    ux, uy, uz = cos(la) * cos(lst), cos(la) * sin(lst), sin(la)
    dot = sx * ux + sy * uy + sz * uz
    dot = -1.0 if dot < -1.0 else 1.0 if dot > 1.0 else dot
    return degrees(asin(dot))
