"""Offline checks for the README and summary caches: python3 tests/test_readme_cache.py"""
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import grove as g  # noqa: E402

failed = []


def check(name, got, want):
    good = got == want
    print(("ok   " if good else "FAIL ") + name + ("" if good else f"\n     got  {got!r}\n     want {want!r}"))
    if not good:
        failed.append(name)


class Stub:
    readmes = {}


tmp = tempfile.mkdtemp()
rd = os.path.join(tmp, "README.md")
BODY = "# T\n\nThis project does something genuinely useful for people every day.\n"
open(rd, "w").write(BODY)
d = {"id": "x", "name": "x", "path": tmp}
s = Stub()
read, summary_of = g.Grove.readme_text, g.Grove.summary_of

check("reads local readme", read(s, d), BODY)
real_open, opens = open, []
g.open = lambda *a, **k: (opens.append(a), real_open(*a, **k))[1]
check("second read is cached", read(s, d), BODY)
check("no disk read on cache hit", opens, [])
del g.open
time.sleep(0.01)
NEW = BODY + "\nMore words here.\n"
open(rd, "w").write(NEW)
check("edit is noticed", read(s, d), NEW)
a = summary_of(s, d, BODY)
check("summary matches summarize", a, g.summarize(BODY)[0])
check("summary memoised", summary_of(s, d, BODY) is a, True)
check("summary refreshed on new text", summary_of(s, d, "# Z\n\nA completely different description that is long enough.\n"),
      "A completely different description that is long enough.")
os.remove(rd)
check("deleted readme falls through", read(s, d), None)
print("ALL OK" if not failed else "FAILED")
sys.exit(1 if failed else 0)
