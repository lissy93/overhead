# A target is anything in the sky we can point at. Each one answers observe()
# with a normalized fix {az, el, name, kind, ...} or None if it cannot right now.
from . import config, iss, planes, planets


class SatTarget:
    kind = "sat"

    def __init__(self, name, catnr, l1, l2):
        self.name = name
        self.catnr = catnr
        self.sat = iss.load_sat(l1, l2)
        self.src = "SEED"

    def set_tle(self, l1, l2):
        s = iss.load_sat(l1, l2)
        if s:
            self.sat, self.src = s, "LIVE"
            return True
        return False

    def observe(self, obs, tm):
        if not self.sat:
            return None
        pos = iss.position(self.sat, tm)
        if not pos:
            return None
        o = iss.observe(pos, obs)
        o["name"] = self.name
        o["kind"] = "sat"
        o["sunlit"] = pos["sunlit"]
        return o

    def next_pass(self, obs, tm):
        return iss.next_pass(self.sat, obs, tm) if self.sat else None


class PlanetTarget:
    kind = "planet"

    def __init__(self, body):
        self.body = body
        self.name = body.upper()
        self.src = "EPHEM"

    def observe(self, obs, tm):
        r = planets.observe(self.body, obs, tm)
        if not r:
            return None
        return {"az": r["az"], "el": r["el"], "name": self.name, "kind": "planet"}

    def next_pass(self, obs, tm):
        return None


class PlaneTarget:
    kind = "plane"

    def __init__(self):
        self.name = "AIRCRAFT"
        self.src = "ADSB"
        self.rows = []

    def set_rows(self, rows):
        self.rows = rows or []

    def observe(self, obs, tm):
        p = planes.nearest(self.rows)
        if not p or p["dir"] is None:
            return None
        return {"az": p["dir"], "el": planes.elevation(p["alt_ft"], p["dst_nm"]),
                "name": self.name, "kind": "plane", "flight": p["flight"],
                "alt_ft": p["alt_ft"], "dst_nm": p["dst_nm"]}

    def next_pass(self, obs, tm):
        return None


def build():
    """The target list. ISS first (index 0), then the rest, then aircraft."""
    ts = [SatTarget(*s) for s in config.SATS]
    ts += [PlanetTarget(b) for b in config.PLANETS]
    ts.append(PlaneTarget())
    return ts
