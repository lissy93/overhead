# Device/sim side. Uses the badge or host `requests` module. Never raises:
# returns (False, None) on any failure so callers fall back to last known data.
from . import log


def safe_fetch(url, timeout=8):
    """Blocking GET -> (ok, json_or_text). Bounded by timeout so a slow or
    dead endpoint can never hang the caller."""
    try:
        import requests
    except ImportError:
        return (False, None)
    r = None
    try:
        try:
            r = requests.get(url, timeout=timeout)
        except TypeError:
            r = requests.get(url)  # ports whose get() lacks a timeout kw
        try:
            data = r.json()
        except Exception:
            data = r.text
        return (True, data)
    except Exception as e:
        log.warn("net", "%s %s" % (url[:30], repr(e)[:40]))
        return (False, None)
    finally:
        if r is not None:
            try:
                r.close()
            except Exception:
                pass


def ensure_wifi():
    """Best effort. The OS brings wifi up when wifi_preference is set."""
    try:
        import wifi
    except ImportError:
        return
    try:
        if not wifi.status():
            wifi.connect()
    except Exception:
        pass
