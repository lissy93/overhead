import math
import time

import app
from events.input import Buttons, BUTTON_TYPES
from system.eventbus import eventbus
from system.patterndisplay.events import PatternDisable
from app_components.notification import Notification
from tildagonos import tildagonos

from .emflib import config, iss, planes, targets, sun, sgp4, log
from .emflib.net import safe_fetch, ensure_wifi
from .emflib.util import guarded
from . import hud

try:
    import _thread
except ImportError:
    _thread = None
try:
    import settings
except ImportError:
    settings = None

DEMO = False  # dev: seed a fake overhead pass to preview the pointer offline

TRAIL_MAX = 30
DARK_ENOUGH = -6.0
LEVEL_TAG = ("idle", "low pass", "good pass", "overhead")


class OverheadApp(app.App):
    def __init__(self):
        super().__init__()
        self.buttons = Buttons(self)
        self.targets = targets.build()
        self.plane_target = self.targets[-1]
        self.mode = 0
        self.obs = None
        self.pass_ = None
        self.track = []
        self.trail = []
        self.status = "STARTING"
        self.iss_naked = False
        self.show_log = False
        self.t = 0
        self._pass_epoch = 0
        self._pass_for = -1
        self._last_level = 0
        self._iss_was_naked = False
        self._iss_was_up = False
        self._tle_queue = [i for i, tg in enumerate(self.targets) if tg.kind == "sat"]
        self._tle_idx = 0
        self._t_pos = 1e9
        self._t_pass = 9e9
        self._t_tle = 3000
        self._t_refresh = 0
        self._t_pln = 1e9
        self._t_pat = 0
        self._t_ntp = 15000
        self.note = None
        self._busy = {"tle": False, "pln": False, "pass": False, "ntp": False}
        self._result = {"tle": None, "pln": None, "pass": None}
        self._load_cached_tles()
        eventbus.emit(PatternDisable())
        log.info("overhead", "up, %d targets" % len(self.targets))
        if DEMO:
            self.obs = {"az": 118.0, "el": 34.0, "ground_km": 700.0, "level": 2,
                        "sunlit": True, "name": "ISS", "kind": "sat"}
            self.iss_naked = True

    # ---- tle cache ----
    def _load_cached_tles(self):
        if not settings:
            return
        try:
            cache = settings.get("overhead", {}).get("tles", {})
        except Exception:
            return
        for tg in self.targets:
            if tg.kind == "sat":
                tle = cache.get(tg.catnr)
                if tle and len(tle) == 2:
                    tg.set_tle(tle[0], tle[1])

    def _save_tle(self, catnr, l1, l2):
        if not settings:
            return
        try:
            cfg = settings.get("overhead", {})
            cache = cfg.get("tles", {})
            cache[catnr] = [l1, l2]
            cfg["tles"] = cache
            settings.set("overhead", cfg)
            settings.save()
        except Exception as e:
            log.warn("overhead", "tle save " + repr(e))

    # ---- input ----
    @guarded("overhead.update")
    def update(self, delta):
        if self.note:
            self.note.update(delta)
        if self.t < 800:
            return True  # ignore button noise for the first moment after launch
        b = self.buttons
        if b.pressed(BUTTON_TYPES["CANCEL"]):
            self._leds_off()
            self.minimise()
            return False
        if b.pressed(BUTTON_TYPES["CONFIRM"]):
            self.show_log = not self.show_log
        if b.pressed(BUTTON_TYPES["RIGHT"]):
            self._switch(1)
        if b.pressed(BUTTON_TYPES["LEFT"]):
            self._switch(-1)
        return True

    def _switch(self, d):
        self.mode = (self.mode + d) % len(self.targets)
        self.obs = None
        self.pass_ = None
        self.track = []
        self.trail = []
        self._pass_for = -1
        self._t_pos = 1e9
        self._t_pass = 9e9
        log.info("overhead", "mode " + self.targets[self.mode].name)

    # ---- loop ----
    @guarded("overhead.bg")
    def background_update(self, delta):
        self.t += delta
        self._t_pat += delta
        if self._t_pat >= 1000:
            self._t_pat = 0
            eventbus.emit(PatternDisable())
        if not DEMO:
            self._tick(delta)
        self._drive_leds()

    def _tick(self, delta):
        # the badge RTC boots at 2000 and the OS never syncs it, so we do
        self._t_ntp += delta
        if self._t_ntp >= 15000 and not self._clock_ok() and not self._busy["ntp"]:
            self._t_ntp = 0
            self._spawn("ntp")
        self._t_pos += delta
        if self._t_pos >= 1000:
            self._t_pos = 0
            self._update_obs()
            self._update_iss_bg()
        cur = self.targets[self.mode]
        self._t_pass += delta
        if cur.kind == "sat" and self._t_pass >= 300000 and self._clock_ok() and not self._busy["pass"]:
            self._t_pass = 0
            self._spawn("pass")
        self._t_tle += delta
        if self._t_tle >= 5000 and self._tle_queue and not self._busy["tle"]:
            self._t_tle = 0
            self._spawn("tle")
        self._t_refresh += delta
        if self._t_refresh >= config.TLE_REFRESH_MS:
            self._t_refresh = 0
            self._tle_queue = [i for i, tg in enumerate(self.targets) if tg.kind == "sat"]
        self._t_pln += delta
        if self._t_pln >= 25000 and not self._busy["pln"]:
            self._t_pln = 0
            self._spawn("pln")
        self._consume()

    def _clock_ok(self):
        return time.gmtime()[0] >= 2024

    def _update_obs(self):
        cur = self.targets[self.mode]
        if cur.kind != "plane" and not self._clock_ok():
            self.obs, self.status, self.trail = None, "NO CLOCK", []
            return
        o = cur.observe(config.LOCATION, time.gmtime())
        self.obs = o
        self.status = "OK" if o else "NO SIGNAL"
        if o and o.get("el", -99) > 0:
            self.trail.append((o["az"], o["el"]))
            if len(self.trail) > TRAIL_MAX:
                del self.trail[0]
            if cur.kind == "sat":
                lvl = o.get("level", 0)
                if lvl >= 1 and lvl > self._last_level:
                    self.note = Notification(cur.name + " " + LEVEL_TAG[lvl])
                self._last_level = lvl
        else:
            self.trail = []
            self._last_level = 0

    def _update_iss_bg(self):
        # the ISS always wins, so watch it even while you look at other things
        if not self._clock_ok():
            return
        tm = time.gmtime()
        o = self.targets[0].observe(config.LOCATION, tm)
        if not o:
            return
        up = o["el"] > 0
        jd = sgp4.jday(tm[0], tm[1], tm[2], tm[3], tm[4], tm[5])
        dark = sun.altitude(config.LOCATION["lat"], config.LOCATION["lon"], jd) < DARK_ENOUGH
        naked = up and bool(o.get("sunlit")) and dark
        if naked and not self._iss_was_naked:
            self.note = Notification("ISS LOOK UP")
            self.mode = 0
            self._t_pos = 1e9
            log.info("overhead", "ISS naked-eye, snapping to it")
        elif up and o.get("level", 0) >= 2 and not self._iss_was_up and self.mode != 0:
            self.note = Notification("ISS overhead")
        self._iss_was_naked = naked
        self._iss_was_up = up
        if self.mode == 0:
            self.iss_naked = naked

    def _countdown(self):
        if not self.pass_:
            return None
        return self._pass_epoch + self.pass_["in_s"] - time.time()

    def _pass_local(self, cd):
        lt = time.gmtime(int(time.time() + cd) + config.TZ_OFFSET_S)
        return "%02d:%02d" % (lt[3], lt[4])

    # ---- workers ----
    def _spawn(self, key):
        if key == "tle":
            self._tle_idx = self._tle_queue.pop(0)
        self._busy[key] = True
        if _thread:
            try:
                _thread.start_new_thread(self._worker, (key,))
                return
            except Exception:
                pass
        self._worker(key)

    def _worker(self, key):
        try:
            if key == "tle":
                tg = self.targets[self._tle_idx]
                self._result["tle"] = (self._tle_idx, iss.fetch_tle(safe_fetch, tg.catnr))
            elif key == "pln":
                ok, raw = safe_fetch(config.URLS["planes"])
                self._result["pln"] = planes.parse(raw) if ok else None
            elif key == "pass":
                idx, tm, ep = self.mode, time.gmtime(), time.time()
                tg = self.targets[idx]
                p = tg.next_pass(config.LOCATION, tm)
                tr = iss.pass_track(tg.sat, config.LOCATION, tm, p["in_s"], p["out_s"]) if p else []
                self._result["pass"] = (idx, p, tr, ep)
            elif key == "ntp":
                ensure_wifi()
                import ntptime
                ntptime.settime()
                log.info("overhead", "clock set %04d-%02d-%02d" % time.gmtime()[:3])
        except Exception as e:
            log.error("overhead.worker", key + " " + repr(e))
        self._busy[key] = False

    def _consume(self):
        r = self._result["tle"]
        if r is not None:
            self._result["tle"] = None
            idx, tle = r
            if tle:
                tg = self.targets[idx]
                if tg.set_tle(tle[0], tle[1]):
                    self._save_tle(tg.catnr, tle[0], tle[1])
                    if idx == self.mode:
                        self._t_pass = 300000
                    log.info("overhead", "tle " + tg.name)
        r = self._result["pass"]
        if r is not None:
            self._result["pass"] = None
            idx, p, tr, ep = r
            if idx == self.mode:
                self.pass_, self.track, self._pass_epoch, self._pass_for = p, tr, ep, idx
        r = self._result["pln"]
        if r is not None:
            self._result["pln"] = None
            self.plane_target.set_rows(r)

    # ---- leds ----
    def _drive_leds(self):
        for i in range(1, 13):
            tildagonos.leds[i] = (0, 0, 0)
        o = self.obs
        cur = self.targets[self.mode]
        if o and o.get("el", -99) > -3:
            if self.mode == 0 and self.iss_naked:
                self._led_lookup(o)
            else:
                self._led_point(o)
        elif cur.kind == "sat" and self.pass_ and self._pass_for == self.mode and self._clock_ok():
            self._led_wait()
        tildagonos.leds.write()

    def _led_point(self, o):
        kind = o.get("kind")
        if kind == "sat":
            lvl = o.get("level", 1)
            col = ((0, 0, 30), (0, 110, 150), (30, 200, 90), (255, 255, 255))[lvl]
            if lvl >= 3:
                k = 0.4 + 0.6 * (0.5 + 0.5 * math.sin(self.t / 180.0))
                col = (int(col[0] * k), int(col[1] * k), int(col[2] * k))
        elif kind == "planet":
            col = (200, 130, 20)
        else:
            col = (0, 110, 150)
        idx = _az_to_led(o["az"])
        tildagonos.leds[idx] = col
        faint = (col[0] // 6, col[1] // 6, col[2] // 6)
        tildagonos.leds[_wrap(idx - 1)] = faint
        tildagonos.leds[_wrap(idx + 1)] = faint

    def _led_lookup(self, o):
        # strobe the whole ring white, you are not allowed to miss this one
        k = 1.0 if (self.t // 250) % 2 == 0 else 0.12
        v = int(230 * k)
        for i in range(1, 13):
            tildagonos.leds[i] = (v, v, v)
        tildagonos.leds[_az_to_led(o["az"])] = (255, 255, 255)

    def _led_wait(self):
        # point at where the pass rises, keener the closer it gets
        cd = self._countdown()
        near = cd is not None and cd < 3600
        rate = 90.0 if near else 320.0
        floor = 0.4 if near else 0.12
        k = floor + (1.0 - floor) * (0.5 + 0.5 * math.sin(self.t / rate))
        idx = _az_to_led(self.pass_["rise_az"])
        tildagonos.leds[idx] = (int(200 * k), int(120 * k), 0)
        faint = (int(36 * k), int(20 * k), 0)
        tildagonos.leds[_wrap(idx - 1)] = faint
        tildagonos.leds[_wrap(idx + 1)] = faint

    def _leds_off(self):
        for i in range(1, 13):
            tildagonos.leds[i] = (0, 0, 0)
        tildagonos.leds.write()

    # ---- draw ----
    @guarded("overhead.draw")
    def draw(self, ctx):
        ctx.save()
        if self.show_log:
            hud.log_overlay(ctx, log.tail(11))
            ctx.restore()
            return
        hud.background(ctx)
        hud.scanlines(ctx)
        hud.bezel(ctx)
        ctx.font = "Comic Mono"
        hud.dome(ctx)
        hud.chevrons(ctx)
        cur = self.targets[self.mode]
        o = self.obs
        if o and o.get("el", -99) > 0:
            self._draw_up(ctx, cur, o)
        else:
            self._draw_down(ctx, cur)
        hud.footer(ctx, "%d/%d  %s" % (self.mode + 1, len(self.targets), self._src(cur)))
        ctx.restore()
        if self.note:
            self.note.draw(ctx)

    def _draw_up(self, ctx, cur, o):
        if self.mode == 0 and self.iss_naked:
            bright = (self.t // 350) % 2 == 0
            hud.title(ctx, "LOOK UP", (1.0, 1.0, 1.0) if bright else hud.AMBER)
        else:
            hud.title(ctx, cur.name, hud.GREEN)
        if cur.kind == "sat":
            hud.arc(ctx, self.track, active=True)
        hud.iss_live(ctx, o, self.trail)
        hud.readout(ctx, o)

    def _draw_down(self, ctx, cur):
        hud.title(ctx, cur.name, hud.AMBER)
        if not self._clock_ok() and cur.kind != "plane":
            hud.status(ctx, ["NO CLOCK", "connect wifi to sync"])
        elif cur.kind == "sat":
            hud.arc(ctx, self.track, active=False)
            cd = self._countdown()
            if self.pass_ and self._pass_for == self.mode and cd is not None:
                hud.readout_wait(ctx, self.pass_, cd, self._pass_local(cd))
            else:
                hud.status(ctx, ["BELOW HORIZON", "finding next pass"])
        elif cur.kind == "planet":
            hud.status(ctx, ["BELOW HORIZON", "wait for it to rise"])
        else:
            hud.status(ctx, ["NO AIRCRAFT", "scanning the sky"])

    def _src(self, cur):
        if cur.kind == "sat":
            return "SGP4 " + cur.src
        if cur.kind == "planet":
            return "EPHEM"
        return "ADSB"


def _az_to_led(az):
    return _wrap(1 + int((az + 15) // 30))


def _wrap(i):
    return 1 + ((i - 1) % 12)


__app_export__ = OverheadApp
