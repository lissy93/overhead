import unittest

from emflib import astro, iss, planes, sgp4, sun, planets, targets, config
from emflib.config import LOCATION
from tests import fixtures as fx

SEED = config.SATS[0][2:4]  # the ISS seed TLE
OVERHEAD = {"lat": 52.0409347, "lon": -2.3767691, "alt_km": 420.0, "sunlit": True}
FARSIDE = {"lat": -49.95, "lon": -44.50, "alt_km": 432.0, "sunlit": True}


class Astro(unittest.TestCase):
    def test_haversine_one_degree(self):
        self.assertTrue(111.0 < astro.haversine_km(0, 0, 0, 1) < 111.5)

    def test_overhead_is_ninety(self):
        az, el, slant = astro.look_angles(LOCATION, LOCATION["lat"], LOCATION["lon"], 420.0)
        self.assertGreater(el, 89.0)
        self.assertTrue(419 < slant < 421, slant)

    def test_compass_point(self):
        self.assertEqual(astro.compass_point(0), "N")
        self.assertEqual(astro.compass_point(90), "E")
        self.assertEqual(astro.compass_point(180), "S")


class Iss(unittest.TestCase):
    def test_overhead_is_top_level(self):
        o = iss.observe(OVERHEAD, LOCATION)
        self.assertGreater(o["el"], 89.0)
        self.assertEqual(o["level"], 3)

    def test_below_horizon_is_idle(self):
        o = iss.observe(FARSIDE, LOCATION)
        self.assertLess(o["el"], 0)
        self.assertEqual(o["level"], 0)

    def test_alert_bands(self):
        self.assertEqual(iss.alert_level(5), 0)
        self.assertEqual(iss.alert_level(15), 1)
        self.assertEqual(iss.alert_level(30), 2)
        self.assertEqual(iss.alert_level(60), 3)

    def test_naked_eye_needs_sun_and_dark(self):
        self.assertTrue(iss.naked_eye({"sunlit": True}, 30.0, is_dark=True))
        self.assertFalse(iss.naked_eye({"sunlit": True}, 30.0, is_dark=False))
        self.assertFalse(iss.naked_eye({"sunlit": None}, 30.0, is_dark=True))


class Sgp4(unittest.TestCase):
    def test_epoch(self):
        self.assertAlmostEqual(sgp4.twoline2rv(*SEED)["jdsatepoch"], 2461237.266407, places=4)

    def test_subpoint_regression(self):
        # pinned to skyfield: ISS seed at 2026-07-16 21:00:00 UTC
        lat, lon, alt = sgp4.subpoint(sgp4.twoline2rv(*SEED), 2026, 7, 16, 21, 0, 0)
        self.assertLess(astro.haversine_km(lat, lon, 46.00188, -41.92034), 1.0)
        self.assertTrue(400 < alt < 440, alt)

    def test_position_shape(self):
        p = iss.position(sgp4.twoline2rv(*SEED), (2026, 7, 16, 21, 0, 0))
        self.assertIsNotNone(p)
        self.assertIn("sunlit", p)


class Sun(unittest.TestCase):
    def test_noon_sun_is_high(self):
        self.assertGreater(sun.altitude(51.48, 0.0, sgp4.jday(2026, 7, 16, 12, 0, 0)), 50)

    def test_midnight_sun_is_down(self):
        self.assertLess(sun.altitude(51.48, 0.0, sgp4.jday(2026, 7, 16, 0, 0, 0)), 0)

    def test_shadow_test(self):
        jd = sgp4.jday(2026, 7, 16, 12, 0, 0)
        s = sun.sun_vector(jd)
        self.assertTrue(sun.is_sunlit((s[0] * 7000, s[1] * 7000, s[2] * 7000), jd))
        self.assertFalse(sun.is_sunlit((-s[0] * 7000, -s[1] * 7000, -s[2] * 7000), jd))


class Planets(unittest.TestCase):
    def test_all_bodies_in_range(self):
        for body in planets.BODIES:
            r = planets.observe(body, LOCATION, (2026, 7, 16, 22, 0, 0))
            self.assertIsNotNone(r, body)
            self.assertTrue(0.0 <= r["az"] < 360.0, (body, r["az"]))
            self.assertTrue(-90.0 <= r["el"] <= 90.0, (body, r["el"]))

    def test_regression(self):
        # pinned to skyfield-validated output (all within ~0.13 deg of truth)
        want = {"moon": (294.30, -4.19), "mars": (10.61, -15.11), "jupiter": (318.87, -8.72)}
        for body, (az, el) in want.items():
            r = planets.observe(body, LOCATION, (2026, 7, 16, 22, 0, 0))
            self.assertAlmostEqual(r["az"], az, delta=0.2, msg=body)
            self.assertAlmostEqual(r["el"], el, delta=0.2, msg=body)


class Targets(unittest.TestCase):
    def test_build(self):
        tl = targets.build()
        self.assertEqual(tl[0].name, "ISS")
        self.assertEqual(tl[0].kind, "sat")
        self.assertEqual(tl[-1].kind, "plane")

    def test_sat_observe(self):
        o = targets.SatTarget(*config.SATS[0]).observe(LOCATION, (2026, 7, 16, 22, 0, 0))
        self.assertEqual(o["kind"], "sat")
        self.assertEqual(o["name"], "ISS")

    def test_planet_observe(self):
        o = targets.PlanetTarget("venus").observe(LOCATION, (2026, 7, 16, 22, 0, 0))
        self.assertEqual(o["kind"], "planet")

    def test_plane_observe(self):
        p = targets.PlaneTarget()
        self.assertIsNone(p.observe(LOCATION, (2026, 7, 16, 22, 0, 0)))
        p.set_rows(planes.parse(fx.PLANES))
        o = p.observe(LOCATION, (2026, 7, 16, 22, 0, 0))
        self.assertEqual(o["kind"], "plane")
        self.assertEqual(o["flight"], "BAW23")


class Passes(unittest.TestCase):
    def test_finds_a_pass_within_24h(self):
        p = iss.next_pass(sgp4.twoline2rv(*SEED), LOCATION, (2026, 7, 16, 12, 0, 0))
        self.assertIsNotNone(p)
        self.assertTrue(10 <= p["max_el"] <= 90, p["max_el"])
        self.assertLess(p["in_s"], p["out_s"])


class Planes(unittest.TestCase):
    def test_nearest_by_distance(self):
        best = planes.nearest(planes.parse(fx.PLANES))
        self.assertEqual(best["flight"], "BAW23")
        self.assertEqual(best["dst_nm"], 6.2)

    def test_alt_key(self):
        self.assertEqual(planes.parse(fx.PLANES_ALT_KEY)[0]["flight"], "TEST1")

    def test_elevation(self):
        self.assertTrue(0 < planes.elevation(36000, 5) < 90)
        self.assertEqual(planes.elevation(None, 5), 0.0)

    def test_empty(self):
        self.assertIsNone(planes.nearest(planes.parse({})))


if __name__ == "__main__":
    unittest.main()
