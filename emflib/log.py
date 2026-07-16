# Tiny logger. Prints for the REPL and keeps the last few lines, so a badge in
# the field can show its own dying words on screen instead of just sulking.
_BUF = []
_MAX = 24
_NAMES = ("DBG", "INF", "WRN", "ERR")
threshold = 1  # INF and up; drop to 0 when you want the firehose


def _emit(lvl, tag, msg):
    if lvl < threshold:
        return
    line = "%s %s %s" % (_NAMES[lvl], tag, msg)
    print(line)
    _BUF.append(line)
    if len(_BUF) > _MAX:
        del _BUF[0]


def debug(tag, msg):
    _emit(0, tag, msg)


def info(tag, msg):
    _emit(1, tag, msg)


def warn(tag, msg):
    _emit(2, tag, msg)


def error(tag, msg):
    _emit(3, tag, msg)


def tail(n=8):
    return _BUF[-n:]
