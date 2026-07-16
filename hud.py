import math

from .emflib.astro import compass_point
from .emflib.util import hms

TAU = 6.28318
R = 66     # sky-dome radius, centred on the round screen so it looks right
CY = 0     # concentric with the display

BG = (0.03, 0.04, 0.05)
SCAN = (0.07, 0.08, 0.09)
GRID = (0.10, 0.15, 0.19)
INK = (0.86, 0.92, 0.97)
DIM = (0.34, 0.42, 0.50)
AMBER = (0.96, 0.72, 0.16)
CYAN = (0.22, 0.80, 1.0)
GREEN = (0.30, 1.0, 0.52)

LEVEL_DOT = ((0.25, 0.55, 0.72), CYAN, GREEN, (1.0, 1.0, 1.0))
LEVEL_TAG = ("IDLE", "LOW PASS", "GOOD PASS", "OVERHEAD")


def project(az, el):
    if el < 0:
        el = 0.0
    r = R * (90.0 - el) / 90.0        # straight up is the centre, horizon is the rim
    a = math.radians(az)
    return math.sin(a) * r, -math.cos(a) * r + CY


def background(ctx):
    ctx.rgb(*BG).rectangle(-120, -120, 240, 240).fill()


def scanlines(ctx):
    ctx.rgb(*SCAN)
    y = -118
    while y < 120:
        ctx.rectangle(-120, y, 240, 1).fill()
        y += 4


def bezel(ctx):
    # instrument frame hugging the round rim, ticks every 15 degrees
    ctx.line_width = 1
    ctx.rgb(0.11, 0.16, 0.20).arc(0, 0, 113, 0, TAU, True).stroke()
    for k in range(24):
        a = k * (TAU / 24.0)
        r1 = 106 if k % 2 else 101
        ctx.rgb(0.20, 0.28, 0.34).move_to(
            math.sin(a) * r1, -math.cos(a) * r1).line_to(
            math.sin(a) * 112, -math.cos(a) * 112).stroke()


def dome(ctx):
    ctx.line_width = 1
    for f in (1.0, 0.62, 0.28):
        ctx.rgb(*GRID).arc(0, CY, R * f, 0, TAU, True).stroke()
    ctx.font_size = 12
    ctx.text_align = ctx.CENTER
    for name, ang in (("N", 0), ("E", 90), ("S", 180), ("W", 270)):
        a = math.radians(ang)
        ctx.rgb(*DIM).move_to(
            math.sin(a) * (R + 12), -math.cos(a) * (R + 12) + CY + 4).text(name)


def title(ctx, text, col=AMBER):
    ctx.text_align = ctx.CENTER
    ctx.font_size = 16
    ctx.rgb(*col).move_to(0, -100).text(text)


def arc(ctx, track, active=False):
    if not track or len(track) < 2:
        return
    col = GREEN if active else (0.24, 0.44, 0.54)
    ctx.line_width = 2 if active else 1
    x0, y0 = project(*track[0])
    ctx.rgb(*col).move_to(x0, y0)
    for az, el in track[1:]:
        x, y = project(az, el)
        ctx.line_to(x, y)
    ctx.stroke()
    for az, el in (track[0], track[-1]):
        x, y = project(az, el)
        ctx.rgb(*col).arc(x, y, 2.5, 0, TAU, True).fill()


def iss_live(ctx, obs, trail):
    n = len(trail)
    for i, point in enumerate(trail):
        x, y = project(point[0], point[1])
        f = (i + 1) / (n + 1.0)        # older tail points fade out
        ctx.rgb(0.18 * f, 0.55 * f, 0.85 * f).arc(x, y, 1.0 + 2.5 * f, 0, TAU, True).fill()
    dot = _dot_color(obs)
    x, y = project(obs["az"], obs["el"])
    a = math.radians(obs["az"])
    xi, yi = math.sin(a) * 26, -math.cos(a) * 26 + CY  # start outside the centre readout
    ctx.line_width = 2
    ctx.rgb(*dot).move_to(xi, yi).line_to(x, y).stroke()
    ctx.rgb(*dot).arc(x, y, 5, 0, TAU, True).fill()


def plane_blip(ctx, p):
    if not p or p.get("dir") is None:
        return
    a = math.radians(p["dir"])         # planes ride the rim at their bearing
    ctx.rgb(0.55, 0.5, 0.2).arc(math.sin(a) * R, -math.cos(a) * R + CY, 2.0, 0, TAU, True).fill()


def _dot_color(o):
    k = o.get("kind")
    if k == "planet":
        return (1.0, 0.82, 0.35)
    if k == "plane":
        return (0.75, 0.75, 0.35)
    return LEVEL_DOT[o.get("level", 1)]


def chevrons(ctx):
    ctx.text_align = ctx.CENTER
    ctx.font_size = 16
    ctx.rgb(0.30, 0.36, 0.42)
    ctx.move_to(-104, 5).text("<")
    ctx.move_to(104, 5).text(">")


def readout(ctx, o):
    ctx.text_align = ctx.CENTER
    kind = o.get("kind")
    if kind == "sat":
        readout_track(ctx, o)
    elif kind == "planet":
        ctx.font_size = 15
        ctx.rgb(*INK).move_to(0, -4).text(
            "az %03d %s  el %+d" % (int(o["az"]), compass_point(o["az"]), int(o["el"])))
        ctx.font_size = 12
        ctx.rgb(*DIM).move_to(0, 16).text("up now")
    else:
        ctx.font_size = 16
        ctx.rgb(*INK).move_to(0, -4).text(((o.get("flight") or "?").strip() or "?")[:8])
        ctx.font_size = 12
        ctx.rgb(*DIM).move_to(0, 16).text(
            "%dft  %dnm" % (int(o.get("alt_ft") or 0), int(o.get("dst_nm") or 0)))


def readout_track(ctx, obs):
    ctx.text_align = ctx.CENTER
    ctx.font_size = 15
    ctx.rgb(*INK).move_to(0, -4).text(
        "az %03d %s  el %+d" % (int(obs["az"]), compass_point(obs["az"]), int(obs["el"])))
    ctx.font_size = 13
    ctx.rgb(*LEVEL_DOT[obs["level"]]).move_to(0, 16).text(
        "%s  %dkm" % (LEVEL_TAG[obs["level"]], int(obs["ground_km"])))


def readout_wait(ctx, pass_, cd, local):
    ctx.text_align = ctx.CENTER
    ctx.font_size = 21
    ctx.rgb(*AMBER).move_to(0, -2).text("T-" + hms(cd))
    ctx.font_size = 12
    ctx.rgb(*DIM).move_to(0, 18).text(
        "%s  %s %d" % (local, compass_point(pass_["rise_az"]), int(pass_["max_el"])))


def status(ctx, lines):
    ctx.text_align = ctx.CENTER
    for i, line in enumerate(lines):
        ctx.font_size = 16 if i == 0 else 13
        ctx.rgb(*(INK if i == 0 else DIM)).move_to(0, -2 + i * 20).text(line)


def footer(ctx, text):
    ctx.text_align = ctx.CENTER
    ctx.font_size = 10
    ctx.rgb(*DIM).move_to(0, 102).text(text)


def log_overlay(ctx, lines):
    ctx.rgb(0.0, 0.0, 0.0).rectangle(-120, -120, 240, 240).fill()
    ctx.text_align = ctx.CENTER
    ctx.font_size = 13
    ctx.rgb(*GREEN).move_to(0, -96).text("LOG")
    ctx.font_size = 11
    y = -74
    for line in lines[-11:]:
        ctx.rgb(*DIM).move_to(0, y).text(line[:36])
        y += 13
