"""Offline checks for the manual update check (check_now, check-all summary): python3 tests/test_updates.py"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import grove as g  # noqa: E402

failed = []


def check(name, got, want):
    good = got == want
    print(("ok   " if good else "FAIL ") + name + ("" if good else f"\n     got  {got!r}\n     want {want!r}"))
    if not good:
        failed.append(name)


class Stub:
    """Just enough of the Grove window to run its update-check methods without a screen."""
    check_now = g.Grove.check_now
    check_all_updates = g.Grove.check_all_updates
    _check_all_done = g.Grove._check_all_done
    cloned = g.Grove.cloned

    def __init__(self, tree, latest):
        self.tree, self.latest = tree, latest   # latest: slug -> release dict or None
        self.latest_tags, self.update_ok, self.untracked_latest = {}, {}, {}
        self.toasts = []

    def latest_release(self, slug, cb):
        cb(self.latest.get(slug))

    def toast(self, msg):
        self.toasts.append(msg)

    def current(self):
        return None

    def refresh_subtitles(self):
        pass


folder = tempfile.mkdtemp()
open(os.path.join(folder, "app"), "w").write("x")


def proj(i, slug, tag=None, path=folder):
    return {"type": "project", "id": i, "name": i, "url": f"https://github.com/{slug}", "path": path,
            "release": {"tag": tag, "kind": "download"} if tag else None}


def run(d, latest):
    s = Stub([d], latest)
    out = []
    s.check_now(d, lambda st, rel: out.append((st, rel and rel["tag"])))
    return s, out[0]


rel2 = {"tag": "v2", "assets": []}
s, r = run(proj("a", "me/a", "v1"), {"me/a": rel2})
check("newer release is found", r, ("newer", "v2"))
check("newer is remembered for the Update button", s.latest_tags.get("a", {}).get("tag"), "v2")

s, r = run(proj("a", "me/a", "v2"), {"me/a": rel2})
check("same tag is up to date", r, ("uptodate", "v2"))
check("up to date is remembered", s.update_ok.get("a"), "v2")

s, r = run(proj("a", "me/a", "v2"), {})
check("GitHub unreachable is an error, not 'up to date'", r, ("error", None))

s, r = run(proj("a", "me/a", None), {"me/a": rel2})
check("an install with no recorded release is 'untracked'", r, ("untracked", "v2"))
check("untracked remembers the latest", s.untracked_latest.get("a", {}).get("tag"), "v2")

s, r = run(proj("a", "me/a", "v1", path=os.path.join(folder, "missing")), {"me/a": rel2})
check("not installed is not checked", r, ("notinstalled", None))

d = proj("a", "me/a", "v1")
d["url"] = ""
s, r = run(d, {})
check("no repository set", r, ("norepo", None))

# check all: one summary toast
tree = [proj("A", "me/a", "v1"), proj("B", "me/b", "v3"), proj("C", "me/c", None), proj("D", "me/d", "v1"),
        {"type": "group", "id": "g", "name": "G", "children": [proj("E", "me/e", "v1")]}]
latest = {"me/a": rel2, "me/b": {"tag": "v3", "assets": []}, "me/c": rel2, "me/e": {"tag": "v1", "assets": []}}
s = Stub(tree, latest)
s.check_all_updates()
check("check all counts the update", "1 update: A v2" in s.toasts[-1], True)
check("check all mentions the untracked one", "no release recorded for C" in s.toasts[-1], True)
check("check all mentions the one it couldn't reach", "couldn't check D" in s.toasts[-1], True)
check("check all looks inside groups", s.update_ok.get("E"), "v1")

tree = [proj("A", "me/a", "v2"), proj("B", "me/b", "v3")]
s = Stub(tree, {"me/a": rel2, "me/b": {"tag": "v3", "assets": []}})
s.check_all_updates()
check("check all says everything is current", s.toasts[-1], "All 2 projects are up to date.")

s = Stub([], {})
s.check_all_updates()
check("check all with nothing installed", s.toasts[-1], "No installed projects to check yet")

print("ALL OK" if not failed else f"FAILED: {failed}")
sys.exit(1 if failed else 0)
