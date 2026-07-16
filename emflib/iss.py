from . import config, sgp4, sun
from .astro import haversine_km, look_angles


def load_sat(l1, l2):
    try:
        return sgp4.twoline2rv(l1, l2)
    except Exception:
        return None


def fetch_tle(safe_fetch, catnr):
    """Pull a fresh TLE for a NORAD catalog number. Returns (l1, l2) or None."""
    ok, raw = safe_fetch(config.TLE_URL % catnr)
    if not ok or not isinstance(raw, str):
        return None
    lines = [x.strip() for x in raw.splitlines() if x.strip()]
    for i in range(len(lines) - 1):
        if lines[i].startswith("1 ") and lines[i + 1].startswith("2 "):
            return (lines[i], lines[i + 1])
    return None


def position(sat, tm):
    """Sub-satellite point plus whether the sun is on it, from a gmtime tuple."""
    try:
        jd = sgp4.jday(tm[0], tm[1], tm[2], tm[3], tm[4], tm[5])
        r = sgp4.propagate(sat, jd)
        if r is None:
            return None
        lat, lon, alt = sgp4.geodetic(r, jd)
    except Exception:
        return None
    return {"lat": lat, "lon": lon, "alt_km": alt, "sunlit": sun.is_sunlit(r, jd)}


def next_pass(sat, obs, tm, search_min=1440, step_s=30):
    """Next pass above ISS_MIN_ELEV. Offsets are seconds from tm, None if none."""
    base = sgp4.jday(tm[0], tm[1], tm[2], tm[3], tm[4], tm[5])
    steps = int(search_min * 60 // step_s)
    in_pass = False
    rise_s = 0
    rise_az = 0.0
    max_el = -90.0
    max_az = 0.0
    for i in range(steps + 1):
        sp = sgp4.subpoint_jd(sat, base + (i * step_s) / 86400.0)
        if sp is None:
            continue
        az, el, _ = look_angles(obs, sp[0], sp[1], sp[2])
        if not in_pass:
            if el >= config.ISS_MIN_ELEV:
                in_pass = True
                rise_s = i * step_s
                rise_az = az
                max_el = el
                max_az = az
        else:
            if el > max_el:
                max_el = el
                max_az = az
            if el < config.ISS_MIN_ELEV:
                return {"in_s": rise_s, "out_s": i * step_s, "max_el": max_el,
                        "max_az": max_az, "rise_az": rise_az}
    return None


def pass_track(sat, obs, tm, in_s, out_s, n=14):
    """Sample (az, el) along a pass so the HUD can draw its arc."""
    base = sgp4.jday(tm[0], tm[1], tm[2], tm[3], tm[4], tm[5])
    span = out_s - in_s
    pts = []
    for i in range(n + 1):
        sp = sgp4.subpoint_jd(sat, base + (in_s + span * i / n) / 86400.0)
        if sp:
            az, el, _ = look_angles(obs, sp[0], sp[1], sp[2])
            pts.append((az, el))
    return pts


def observe(iss, obs):
    az, el, slant = look_angles(obs, iss["lat"], iss["lon"], iss["alt_km"])
    ground = haversine_km(obs["lat"], obs["lon"], iss["lat"], iss["lon"])
    return {"az": az, "el": el, "slant_km": slant, "ground_km": ground,
            "level": alert_level(el), "sunlit": iss.get("sunlit")}


def alert_level(el):
    """0 idle, 1 low pass, 2 good pass, 3 overhead show."""
    if el < config.ISS_MIN_ELEV:
        return 0
    if el < config.ISS_GOOD_ELEV:
        return 1
    if el < config.ISS_HIGH_ELEV:
        return 2
    return 3


def naked_eye(iss, el, is_dark):
    return el >= config.ISS_MIN_ELEV and bool(iss.get("sunlit")) and is_dark
