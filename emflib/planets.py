# Low-precision planet and moon positions (Paul Schlyter's method), good to a
# couple of arcminutes, which is ample for pointing a badge at the sky.
from math import sin, cos, tan, asin, atan2, sqrt, radians, degrees, pi

from .sgp4 import gmst, jday

_2PI = 2.0 * pi
BODIES = ("mercury", "venus", "mars", "jupiter", "saturn", "moon")

# [N, i, w, a, e, M] each as (value, per-day rate), angles in degrees, a in AU
_EL = {
    "mercury": (48.3313, 3.24587e-5, 7.0047, 5.00e-8, 29.1241, 1.01444e-5,
                0.387098, 0.0, 0.205635, 5.59e-10, 168.6562, 4.0923344368),
    "venus": (76.6799, 2.46590e-5, 3.3946, 2.75e-8, 54.8910, 1.38374e-5,
              0.723330, 0.0, 0.006773, -1.302e-9, 48.0052, 1.6021302244),
    "mars": (49.5574, 2.11081e-5, 1.8497, -1.78e-8, 286.5016, 2.92961e-5,
             1.523688, 0.0, 0.093405, 2.516e-9, 18.6021, 0.5240207766),
    "jupiter": (100.4542, 2.76854e-5, 1.3030, -1.557e-7, 273.8777, 1.64505e-5,
                5.20256, 0.0, 0.048498, 4.469e-9, 19.8950, 0.0830853001),
    "saturn": (113.6634, 2.38980e-5, 2.4886, -1.081e-7, 339.3939, 2.97661e-5,
               9.55475, 0.0, 0.055546, -9.499e-9, 316.9670, 0.0334442282),
}


def _rev(x):
    return x - 360.0 * (x // 360.0)  # wrap to 0..360 without fmod fuss


def _kepler(M, e):
    # eccentric anomaly by newton, M and e small so it settles fast
    E = M + e * sin(M)
    for _ in range(6):
        E = E - (E - e * sin(E) - M) / (1.0 - e * cos(E))
    return E


def _obliquity(d):
    return radians(23.4393 - 3.563e-7 * d)  # tilt of the earth, slowly drifting


def _sun_rect(d):
    # the sun in ecliptic rectangular coords, needed to go heliocentric->geocentric
    w = radians(_rev(282.9404 + 4.70935e-5 * d))
    e = 0.016709 - 1.151e-9 * d
    M = radians(_rev(356.0470 + 0.9856002585 * d))
    E = _kepler(M, e)
    xv = cos(E) - e
    yv = sqrt(1.0 - e * e) * sin(E)
    r = sqrt(xv * xv + yv * yv)
    lon = atan2(yv, xv) + w
    return r * cos(lon), r * sin(lon)


def _planet_radec(key, d):
    t = _EL[key]
    N = radians(_rev(t[0] + t[1] * d))
    i = radians(t[2] + t[3] * d)
    w = radians(_rev(t[4] + t[5] * d))
    a = t[6] + t[7] * d
    e = t[8] + t[9] * d
    M = radians(_rev(t[10] + t[11] * d))

    E = _kepler(M, e)
    xv = a * (cos(E) - e)
    yv = a * sqrt(1.0 - e * e) * sin(E)
    r = sqrt(xv * xv + yv * yv)
    vw = atan2(yv, xv) + w
    # heliocentric ecliptic, then shift by the sun to get geocentric
    xh = r * (cos(N) * cos(vw) - sin(N) * sin(vw) * cos(i))
    yh = r * (sin(N) * cos(vw) + cos(N) * sin(vw) * cos(i))
    zh = r * sin(vw) * sin(i)
    xs, ys = _sun_rect(d)
    xg, yg, zg = xh + xs, yh + ys, zh
    return _ecl_to_radec(xg, yg, zg, d)


def _ecl_to_radec(xg, yg, zg, d):
    ecl = _obliquity(d)
    xe = xg
    ye = yg * cos(ecl) - zg * sin(ecl)
    ze = yg * sin(ecl) + zg * cos(ecl)
    ra = atan2(ye, xe) % _2PI
    dec = atan2(ze, sqrt(xe * xe + ye * ye))
    return ra, dec


def _moon_radec(d, obs, jd):
    N = radians(_rev(125.1228 - 0.0529538083 * d))
    i = radians(5.1454)
    w = radians(_rev(318.0634 + 0.1643573223 * d))
    a = 60.2666  # earth radii
    e = 0.054900
    M = radians(_rev(115.3654 + 13.0649929509 * d))

    E = _kepler(M, e)
    xv = a * (cos(E) - e)
    yv = a * sqrt(1.0 - e * e) * sin(E)
    r = sqrt(xv * xv + yv * yv)
    v = atan2(yv, xv)
    vw = v + w
    xh = r * (cos(N) * cos(vw) - sin(N) * sin(vw) * cos(i))
    yh = r * (sin(N) * cos(vw) + cos(N) * sin(vw) * cos(i))
    zh = r * sin(vw) * sin(i)

    lon = atan2(yh, xh)
    lat = atan2(zh, sqrt(xh * xh + yh * yh))

    # the moon wobbles, so add the big perturbation terms (Schlyter)
    Ms = radians(_rev(356.0470 + 0.9856002585 * d))       # sun mean anomaly
    Ls = radians(_rev(282.9404 + 4.70935e-5 * d)) + Ms    # sun mean longitude
    Lm = N + w + M                                        # moon mean longitude
    D = Lm - Ls                                           # mean elongation
    F = Lm - N                                            # argument of latitude
    lon += radians(
        -1.274 * sin(M - 2 * D) + 0.658 * sin(2 * D) - 0.186 * sin(Ms)
        - 0.059 * sin(2 * M - 2 * D) - 0.057 * sin(M - 2 * D + Ms)
        + 0.053 * sin(M + 2 * D) + 0.046 * sin(2 * D - Ms) + 0.041 * sin(M - Ms)
        - 0.035 * sin(D) - 0.031 * sin(M + Ms) - 0.015 * sin(2 * F - 2 * D)
        + 0.011 * sin(M - 4 * D))
    lat += radians(
        -0.173 * sin(F - 2 * D) - 0.055 * sin(M - F - 2 * D)
        - 0.046 * sin(M + F - 2 * D) + 0.033 * sin(F + 2 * D)
        + 0.017 * sin(2 * M + F))
    r += -0.58 * cos(M - 2 * D) - 0.46 * cos(2 * D)

    xg = r * cos(lon) * cos(lat)
    yg = r * sin(lon) * cos(lat)
    zg = r * sin(lat)
    ra, dec = _ecl_to_radec(xg, yg, zg, d)

    # the moon is close, so correct geocentric -> topocentric (parallax ~1 deg)
    mpar = asin(1.0 / r)
    gclat = radians(obs["lat"]) - radians(0.1924) * sin(2 * radians(obs["lat"]))
    rho = 0.99833 + 0.00167 * cos(2 * radians(obs["lat"]))
    lst = gmst(jd) + radians(obs["lon"])
    ha = lst - ra
    g = atan2(tan(gclat), cos(ha)) if cos(ha) != 0 else gclat
    ra = ra - mpar * rho * cos(gclat) * sin(ha) / cos(dec)
    if sin(g) != 0:
        dec = dec - mpar * rho * sin(gclat) * sin(g - dec) / sin(g)
    return ra, dec


def _azel(ra, dec, obs, jd):
    lst = gmst(jd) + radians(obs["lon"])   # where the observer's meridian points
    ha = lst - ra                          # hour angle of the body
    lat = radians(obs["lat"])
    sinalt = sin(dec) * sin(lat) + cos(dec) * cos(lat) * cos(ha)
    sinalt = -1.0 if sinalt < -1.0 else 1.0 if sinalt > 1.0 else sinalt
    el = degrees(asin(sinalt))
    az = atan2(sin(ha), cos(ha) * sin(lat) - tan(dec) * cos(lat))
    az = (degrees(az) + 180.0) % 360.0     # from-south to compass bearing
    return az, el


def observe(body, obs, tm):
    """(az, el) of a planet or the moon from obs at a gmtime tuple, or None."""
    try:
        jd = jday(tm[0], tm[1], tm[2], tm[3], tm[4], tm[5])
        d = jd - 2451543.5
        if body == "moon":
            ra, dec = _moon_radec(d, obs, jd)
        else:
            ra, dec = _planet_radec(body, d)
        az, el = _azel(ra, dec, obs, jd)
        return {"az": az, "el": el}
    except Exception:
        return None
