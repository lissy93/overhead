# Real payloads captured from the live endpoints, for the parser tests.

# opendata.adsb.fi/api/v2/... (first row real, second synthesized nearer)
PLANES = {
    "now": 1784122090.0,
    "aircraft": [
        {"hex": "3949f0", "flight": "AFR344  ", "t": "B772",
         "alt_baro": 36000, "gs": 484.0, "track": 297.57,
         "lat": 52.388864, "lon": -3.298567, "dst": 39.705, "dir": 302.2},
        {"hex": "40abc1", "flight": "BAW23  ", "t": "A320",
         "alt_baro": 12000, "lat": 52.05, "lon": -2.30, "dst": 6.2, "dir": 95.0},
    ],
}

# airplanes.live uses the key "ac" instead of "aircraft"
PLANES_ALT_KEY = {"ac": [{"hex": "abc", "flight": "TEST1 ", "alt_baro": 5000,
                          "dst": 3.0, "dir": 10.0}]}
