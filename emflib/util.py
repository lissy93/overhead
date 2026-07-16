from . import log


def guarded(tag):
    """Wrap a method so a stray exception is logged, not fatal. The app keeps
    breathing even if one frame or one poll has a bad day."""
    def deco(fn):
        def wrap(*a, **k):
            try:
                return fn(*a, **k)
            except Exception as e:
                log.error(tag, repr(e))
        return wrap
    return deco


def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def hms(sec):
    """Seconds to a compact countdown: 2h27m, 4m12s, or 38s."""
    sec = int(sec)
    if sec < 0:
        sec = 0
    if sec >= 3600:
        return "%dh%02dm" % (sec // 3600, (sec % 3600) // 60)
    if sec >= 60:
        return "%dm%02ds" % (sec // 60, sec % 60)
    return "%ds" % sec
