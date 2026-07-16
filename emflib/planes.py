from math import atan2, degrees


def elevation(alt_ft, dst_nm):
    # rough angle above the horizon from a plane's height and ground distance
    if alt_ft is None or dst_nm is None:
        return 0.0
    alt_km = alt_ft * 0.0003048
    dst_km = dst_nm * 1.852
    if dst_km <= 0:
        return 90.0
    return degrees(atan2(alt_km, dst_km))


def parse(raw):
    """adsb.fi / airplanes.live payload -> list of aircraft dicts."""
    rows = raw.get("aircraft")
    if rows is None:
        rows = raw.get("ac", [])
    out = []
    for a in rows:
        out.append({
            "id": a.get("hex", ""),
            "flight": (a.get("flight") or "").strip(),
            "alt_ft": _num(a.get("alt_baro")),
            "dst_nm": _num(a.get("dst")),
            "dir": _num(a.get("dir")),
            "type": a.get("t", ""),
        })
    return out


def nearest(planes):
    best = None
    for p in planes:
        d = p["dst_nm"]
        if d is None:
            continue
        if best is None or d < best["dst_nm"]:
            best = p
    return best


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None
