# Fixed site: Eastnor Castle Deer Park, EMF 2026. The badge has no GPS.
LOCATION = {"lat": 52.0409347, "lon": -2.3767691, "elev": 110.0}

EVENT = {"name": "EMF 2026", "start": "2026-07-16", "end": "2026-07-19", "tz": "Europe/London"}
TZ_OFFSET_S = 3600  # Europe/London is BST in July

# ISS overhead bands, degrees of elevation above the horizon.
# elev >= 10 gives roughly 4-6 crossings/day at this latitude.
ISS_MIN_ELEV = 10.0
ISS_GOOD_ELEV = 25.0
ISS_HIGH_ELEV = 45.0

URLS = {
    "planes": "https://opendata.adsb.fi/api/v2/lat/52.0409/lon/-2.3768/dist/40",
    "weather": "https://api.open-meteo.com/v1/forecast?latitude=52.0409&longitude=-2.3768&current_weather=true",
    "talks": "https://www.emfcamp.org/schedule/now-and-next.json",
}

# We propagate satellites on-device with SGP4, so the only network they need is
# an occasional fresh TLE. Celestrak is rock solid, unlike the position APIs.
TLE_URL = "https://celestrak.org/NORAD/elements/gp.php?CATNR=%s&FORMAT=TLE"
TLE_REFRESH_MS = 6 * 3600 * 1000

# Satellite catalog. Each ships a recent seed TLE so a fresh badge works with no
# wifi, then refreshes from Celestrak. ISS is first, it stays the star of the show.
SATS = (
    ("ISS", "25544",
     "1 25544U 98067A   26196.76640667  .00004078  00000+0  82095-4 0  9992",
     "2 25544  51.6311 158.6576 0006718 300.0875  59.9447 15.49019038576187"),
    ("CSS", "48274",
     "1 48274U 21035A   26196.53543323  .00001219  00000+0  20014-4 0  9991",
     "2 48274  41.4690 149.7716 0002229 300.3824  59.6794 15.58093729297592"),
    ("HUBBLE", "20580",
     "1 20580U 90037B   26197.21735951  .00003185  00000+0  95693-4 0  9994",
     "2 20580  28.4722 242.1156 0002182 113.0880 246.9946 15.31066694793029"),
)

# Naked-eye planets plus the moon, drawn from on-device ephemeris (no network).
PLANETS = ("moon", "venus", "mars", "jupiter", "saturn")

MQTT = {
    "host": "mqtt.emf.camp",
    "port": 1883,
    "coffee_topic": "overbrewed/coffees",
    "coffee_standin": "phones/total-calls",  # live now, used to test plumbing pre-event
    "weather_topic": "weather/hq",
}

VENUES = ["Stage A", "Stage B", "Stage C", "Workshop 1", "Workshop 2"]
