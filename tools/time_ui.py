"""Time Grove's window build, rebuild and search against a copy of your config (headless-ish; needs a display).
Usage: python3 tools/time_ui.py [config.json]. Uses temp XDG dirs and a distinct APP_ID, so it never touches the running Grove."""
import os
import shutil
import sys
import tempfile
import time

tmp = tempfile.mkdtemp()
for k in ("CONFIG", "DATA", "CACHE"):
    os.environ[f"XDG_{k}_HOME"] = os.path.join(tmp, k.lower())
src = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/.config/grove/config.json")
if os.path.exists(src):
    os.makedirs(os.path.join(tmp, "config", "grove"))
    shutil.copy(src, os.path.join(tmp, "config", "grove", "config.json"))
os.environ.setdefault("GSK_RENDERER", "cairo")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
t0 = time.perf_counter()
import grove as g  # noqa: E402
g.APP_ID = "io.github.grove.TimeUi"
print(f"import        {1000 * (time.perf_counter() - t0):7.1f} ms")
from gi.repository import GLib  # noqa: E402


class A(g.App):
    def do_activate(self):
        t = time.perf_counter()
        win = g.Grove(self)
        print(f"window build  {1000 * (time.perf_counter() - t):7.1f} ms")
        for label, fn in (("rebuild x20", lambda: [win.rebuild() for _ in range(20)]),
                          ("search x20", lambda: [(setattr(win, "query", q), win.rebuild()) for q in ["g", "gr", "gro"] * 7][:20])):
            t = time.perf_counter()
            fn()
            print(f"{label:13} {1000 * (time.perf_counter() - t):7.1f} ms")
        win.query = ""
        GLib.timeout_add(300, self.quit)


sys.exit(A().run([]))
