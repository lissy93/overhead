# A small near-earth SGP4. The ISS orbits every ~92 min, well under the 225 min
# deep-space cutoff, so we get to skip the scary half of the algorithm.
from math import sin, cos, sqrt, atan2, fmod, pi, radians, degrees, floor

_2PI = 2.0 * pi
_D2R = pi / 180.0
_X2O3 = 2.0 / 3.0

# wgs72, because that is the gravity model SGP4 was raised on
_RE = 6378.135
_XKE = 60.0 / sqrt(_RE * _RE * _RE / 398600.8)
_J2 = 0.001082616
_J3 = -0.00000253881
_J4 = -0.00000165597
_J3OJ2 = _J3 / _J2


def jday(y, mon, d, hr, minute, sec):
    return (367.0 * y - floor(7 * (y + floor((mon + 9) / 12.0)) * 0.25)
            + floor(275 * mon / 9.0) + d + 1721013.5
            + ((sec / 60.0 + minute) / 60.0 + hr) / 24.0)


def gmst(jd):
    t = (jd - 2451545.0) / 36525.0
    s = (67310.54841 + (876600.0 * 3600.0 + 8640184.812866) * t
         + 0.093104 * t * t - 6.2e-6 * t * t * t)
    return radians(fmod(s, 86400.0) / 240.0) % _2PI


def _expfield(s):
    s = s.strip()
    if not s:
        return 0.0
    sign = 1.0
    if s[0] in "+-":
        sign = -1.0 if s[0] == "-" else 1.0
        s = s[1:]
    mant, exp = s, "0"
    for i in range(1, len(s)):
        if s[i] in "+-":
            mant, exp = s[:i], s[i:]
            break
    if not mant:
        return 0.0
    return sign * float("0." + mant) * (10.0 ** int(exp))


def twoline2rv(l1, l2):
    epochyr = int(l1[18:20])
    epochdays = float(l1[20:32])
    bstar = _expfield(l1[53:61])
    inclo = float(l2[8:16]) * _D2R
    nodeo = float(l2[17:25]) * _D2R
    ecco = float("0." + l2[26:33].strip())
    argpo = float(l2[34:42]) * _D2R
    mo = float(l2[43:51]) * _D2R
    no = float(l2[52:63]) * (_2PI / 1440.0)

    year = epochyr + (2000 if epochyr < 57 else 1900)
    jdsatepoch = jday(year, 1, 1, 0, 0, 0) + (epochdays - 1.0)

    s = {"bstar": bstar, "inclo": inclo, "nodeo": nodeo, "ecco": ecco,
         "argpo": argpo, "mo": mo, "no": no, "jdsatepoch": jdsatepoch}
    _init(s)
    return s


def _init(s):
    ecco = s["ecco"]; inclo = s["inclo"]; no = s["no"]
    argpo = s["argpo"]; mo = s["mo"]; bstar = s["bstar"]

    cosio = cos(inclo); cosio2 = cosio * cosio
    omeosq = 1.0 - ecco * ecco; rteosq = sqrt(omeosq)

    # un-kozai the mean motion (the TLE lies a little, we un-lie it)
    ak = (_XKE / no) ** _X2O3
    d1 = 0.75 * _J2 * (3.0 * cosio2 - 1.0) / (rteosq * omeosq)
    de = d1 / (ak * ak)
    adel = ak * (1.0 - de * de - de * (1.0 / 3.0 + 134.0 * de * de / 81.0))
    de = d1 / (adel * adel)
    no = no / (1.0 + de)

    ao = (_XKE / no) ** _X2O3
    sinio = sin(inclo)
    po = ao * omeosq
    con42 = 1.0 - 5.0 * cosio2
    con41 = -con42 - cosio2 - cosio2
    posq = po * po
    rp = ao * (1.0 - ecco)

    s["no"] = no
    s["con41"] = con41
    s["x1mth2"] = 1.0 - cosio2
    s["x7thm1"] = 7.0 * cosio2 - 1.0

    ss = 78.0 / _RE + 1.0
    qzms2t = ((120.0 - 78.0) / _RE) ** 4
    isimp = 1 if rp < (220.0 / _RE + 1.0) else 0
    sfour = ss; qzms24 = qzms2t
    perige = (rp - 1.0) * _RE
    if perige < 156.0:
        sfour = 20.0 if perige < 98.0 else perige - 78.0
        qzms24 = ((120.0 - sfour) / _RE) ** 4
        sfour = sfour / _RE + 1.0

    pinvsq = 1.0 / posq
    tsi = 1.0 / (ao - sfour)
    eta = ao * ecco * tsi
    etasq = eta * eta
    eeta = ecco * eta
    psisq = abs(1.0 - etasq)
    coef = qzms24 * tsi ** 4
    coef1 = coef / psisq ** 3.5
    cc2 = coef1 * no * (ao * (1.0 + 1.5 * etasq + eeta * (4.0 + etasq))
          + 0.375 * _J2 * tsi / psisq * con41 * (8.0 + 3.0 * etasq * (8.0 + etasq)))
    cc1 = bstar * cc2
    cc3 = 0.0
    if ecco > 1e-4:
        cc3 = -2.0 * coef * tsi * _J3OJ2 * no * sinio / ecco
    x1mth2 = 1.0 - cosio2
    cc4 = 2.0 * no * coef1 * ao * omeosq * (
        eta * (2.0 + 0.5 * etasq) + ecco * (0.5 + 2.0 * etasq)
        - _J2 * tsi / (ao * psisq) * (
            -3.0 * con41 * (1.0 - 2.0 * eeta + etasq * (1.5 - 0.5 * eeta))
            + 0.75 * x1mth2 * (2.0 * etasq - eeta * (1.0 + etasq)) * cos(2.0 * argpo)))
    cc5 = 2.0 * coef1 * ao * omeosq * (1.0 + 2.75 * (etasq + eeta) + eeta * etasq)
    cosio4 = cosio2 * cosio2
    temp1 = 1.5 * _J2 * pinvsq * no
    temp2 = 0.5 * temp1 * _J2 * pinvsq
    temp3 = -0.46875 * _J4 * pinvsq * pinvsq * no
    mdot = (no + 0.5 * temp1 * rteosq * con41
            + 0.0625 * temp2 * rteosq * (13.0 - 78.0 * cosio2 + 137.0 * cosio4))
    argpdot = (-0.5 * temp1 * con42 + 0.0625 * temp2 * (7.0 - 114.0 * cosio2 + 395.0 * cosio4)
               + temp3 * (3.0 - 36.0 * cosio2 + 49.0 * cosio4))
    xhdot1 = -temp1 * cosio
    nodedot = xhdot1 + (0.5 * temp2 * (4.0 - 19.0 * cosio2)
                        + 2.0 * temp3 * (3.0 - 7.0 * cosio2)) * cosio

    s["isimp"] = isimp
    s["cc1"] = cc1
    s["cc4"] = cc4
    s["cc5"] = cc5
    s["mdot"] = mdot
    s["argpdot"] = argpdot
    s["nodedot"] = nodedot
    s["nodecf"] = 3.5 * omeosq * xhdot1 * cc1
    s["t2cof"] = 1.5 * cc1
    s["omgcof"] = bstar * cc3 * cos(argpo)
    s["xmcof"] = -_X2O3 * coef * bstar / eeta if ecco > 1e-4 else 0.0
    s["eta"] = eta
    s["sinmao"] = sin(mo)
    s["delmo"] = (1.0 + eta * cos(mo)) ** 3
    if abs(cosio + 1.0) > 1.5e-12:
        s["xlcof"] = -0.25 * _J3OJ2 * sinio * (3.0 + 5.0 * cosio) / (1.0 + cosio)
    else:
        s["xlcof"] = -0.25 * _J3OJ2 * sinio * (3.0 + 5.0 * cosio) / 1.5e-12
    s["aycof"] = -0.5 * _J3OJ2 * sinio

    s["d2"] = s["d3"] = s["d4"] = 0.0
    s["t3cof"] = s["t4cof"] = s["t5cof"] = 0.0
    if isimp != 1:
        cc1sq = cc1 * cc1
        d2 = 4.0 * ao * tsi * cc1sq
        temp = d2 * tsi * cc1 / 3.0
        d3 = (17.0 * ao + sfour) * temp
        d4 = 0.5 * temp * ao * tsi * (221.0 * ao + 31.0 * sfour) * cc1
        s["d2"] = d2; s["d3"] = d3; s["d4"] = d4
        s["t3cof"] = d2 + 2.0 * cc1sq
        s["t4cof"] = 0.25 * (3.0 * d3 + cc1 * (12.0 * d2 + 10.0 * cc1sq))
        s["t5cof"] = 0.2 * (3.0 * d4 + 12.0 * cc1 * d3 + 6.0 * d2 * d2
                            + 15.0 * cc1sq * (2.0 * d2 + cc1sq))


def sgp4(s, tsince):
    """Position in the TEME frame (km) at tsince minutes past epoch, or None."""
    no = s["no"]
    xmdf = s["mo"] + s["mdot"] * tsince
    argpdf = s["argpo"] + s["argpdot"] * tsince
    nodedf = s["nodeo"] + s["nodedot"] * tsince
    argpm = argpdf; mm = xmdf
    t2 = tsince * tsince
    nodem = nodedf + s["nodecf"] * t2
    tempa = 1.0 - s["cc1"] * tsince
    tempe = s["bstar"] * s["cc4"] * tsince
    templ = s["t2cof"] * t2
    if s["isimp"] != 1:
        delomg = s["omgcof"] * tsince
        delm = s["xmcof"] * ((1.0 + s["eta"] * cos(xmdf)) ** 3 - s["delmo"])
        temp = delomg + delm
        mm = xmdf + temp
        argpm = argpdf - temp
        t3 = t2 * tsince; t4 = t3 * tsince
        tempa = tempa - s["d2"] * t2 - s["d3"] * t3 - s["d4"] * t4
        tempe = tempe + s["bstar"] * s["cc5"] * (sin(mm) - s["sinmao"])
        templ = templ + s["t3cof"] * t3 + t4 * (s["t4cof"] + tsince * s["t5cof"])

    am = (_XKE / no) ** _X2O3 * tempa * tempa
    em = s["ecco"] - tempe
    if em >= 1.0 or em < -0.001:
        return None
    if em < 1e-6:
        em = 1e-6
    mm = mm + no * templ
    xlm = mm + argpm + nodem
    nodem = nodem % _2PI
    argpm = argpm % _2PI
    xlm = xlm % _2PI
    mm = (xlm - argpm - nodem) % _2PI

    axnl = em * cos(argpm)
    temp = 1.0 / (am * (1.0 - em * em))
    aynl = em * sin(argpm) + temp * s["aycof"]
    xl = mm + argpm + nodem + temp * s["xlcof"] * axnl

    # kepler by newton-raphson; ten iterations is generous for a tame orbit
    u = (xl - nodem) % _2PI
    eo1 = u; tem5 = 9999.9; ktr = 0
    sineo1 = coseo1 = 0.0
    while abs(tem5) >= 1e-12 and ktr < 10:
        sineo1 = sin(eo1); coseo1 = cos(eo1)
        tem5 = 1.0 - coseo1 * axnl - sineo1 * aynl
        tem5 = (u - aynl * coseo1 + axnl * sineo1 - eo1) / tem5
        if abs(tem5) >= 0.95:
            tem5 = 0.95 if tem5 > 0 else -0.95
        eo1 = eo1 + tem5
        ktr += 1

    ecose = axnl * coseo1 + aynl * sineo1
    esine = axnl * sineo1 - aynl * coseo1
    el2 = axnl * axnl + aynl * aynl
    pl = am * (1.0 - el2)
    if pl < 0.0:
        return None
    rl = am * (1.0 - ecose)
    betal = sqrt(1.0 - el2)
    temp = esine / (1.0 + betal)
    sinu = am / rl * (sineo1 - aynl - axnl * temp)
    cosu = am / rl * (coseo1 - axnl + aynl * temp)
    su = atan2(sinu, cosu)
    sin2u = (cosu + cosu) * sinu
    cos2u = 1.0 - 2.0 * sinu * sinu
    temp = 1.0 / pl
    temp1 = 0.5 * _J2 * temp
    temp2 = temp1 * temp

    cosio = cos(s["inclo"]); sinio = sin(s["inclo"])
    mrt = rl * (1.0 - 1.5 * temp2 * betal * s["con41"]) + 0.5 * temp1 * s["x1mth2"] * cos2u
    su = su - 0.25 * temp2 * s["x7thm1"] * sin2u
    xnode = nodem + 1.5 * temp2 * cosio * sin2u
    xinc = s["inclo"] + 1.5 * temp2 * cosio * sinio * cos2u

    sinsu = sin(su); cossu = cos(su)
    snod = sin(xnode); cnod = cos(xnode)
    sini = sin(xinc); cosi = cos(xinc)
    xmx = -snod * cosi
    xmy = cnod * cosi
    ux = xmx * sinsu + cnod * cossu
    uy = xmy * sinsu + snod * cossu
    uz = sini * sinsu
    return (mrt * ux * _RE, mrt * uy * _RE, mrt * uz * _RE)


def _ecef_to_geodetic(x, y, z):
    a = 6378.137
    e2 = 0.0066943799901414
    lon = atan2(y, x)
    p = sqrt(x * x + y * y)
    lat = atan2(z, p)
    alt = 0.0
    for _ in range(6):
        sinlat = sin(lat)
        n = a / sqrt(1.0 - e2 * sinlat * sinlat)
        alt = p / cos(lat) - n
        lat = atan2(z, p * (1.0 - e2 * n / (n + alt)))
    return degrees(lat), degrees(lon), alt


def propagate(sat, jd):
    """TEME position in km at a julian date, or None if the orbit has decayed."""
    return sgp4(sat, (jd - sat["jdsatepoch"]) * 1440.0)


def geodetic(r, jd):
    theta = gmst(jd)
    x, y, z = r
    # spin the inertial vector by sidereal time into an earth-fixed one
    xe = x * cos(theta) + y * sin(theta)
    ye = -x * sin(theta) + y * cos(theta)
    lat, lon, alt = _ecef_to_geodetic(xe, ye, z)
    if lon > 180.0:
        lon -= 360.0
    elif lon < -180.0:
        lon += 360.0
    return lat, lon, alt


def subpoint_jd(sat, jd):
    r = propagate(sat, jd)
    return geodetic(r, jd) if r else None


def subpoint(sat, y, mon, d, hr, minute, sec):
    return subpoint_jd(sat, jday(y, mon, d, hr, minute, sec))
