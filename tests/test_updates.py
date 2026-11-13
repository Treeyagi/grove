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

# ---- after a downloaded update, install.sh runs again (it copies the program elsewhere, e.g. ~/.local/share) ----
import subprocess  # noqa: E402


class Proc:
    def __init__(self, rc):
        self.rc = rc

    def get_exit_status(self):
        return self.rc


class UpdStub:
    """Enough of the window for _updated, with run_async really running the command (no token, as in Grove)."""
    _updated = g.Grove._updated
    fill_missing = g.Grove.fill_missing

    def __init__(self):
        self.latest_tags, self.toasts, self.rebuilt, self.ran = {"P": {"tag": "v2"}}, [], [], []

    def toast(self, msg):
        self.toasts.append(msg)

    def rebuild(self, pid):
        self.rebuilt.append(pid)

    def save(self):
        pass

    def run_async(self, argv, cb, slug=None, token=False):
        self.ran.append((argv, slug, token))
        r = subprocess.run(argv, capture_output=True, text=True, timeout=10)
        cb(Proc(r.returncode), r.stdout, r.stderr)


def updated_project(script):
    path = tempfile.mkdtemp()
    open(os.path.join(path, "app"), "w").write("x")
    if script is not None:
        sh = os.path.join(path, "install.sh")
        open(sh, "w").write("#!/bin/sh\n" + script)
        os.chmod(sh, 0o755)
    d = {"id": "P", "name": "Med", "path": path, "install": "", "run": "",
         "release": {"tag": "v2", "kind": "download", "asset": "med.zip"}}
    s = UpdStub()
    s._updated(d, {"tag": "v2"}, True)
    return s, d, path


# read waits for a keyboard: it must get end-of-input instead of hanging the update
s, d, path = updated_project('read x; pwd > installed-here; echo "$GH_TOKEN" > token-seen\n')
check("update re-runs install.sh", os.path.exists(os.path.join(path, "installed-here")), True)
check("install.sh runs inside the new folder",
      open(os.path.join(path, "installed-here")).read().strip(), os.path.realpath(path))
check("install.sh is not handed a token", (s.ran[0][1], s.ran[0][2], open(os.path.join(path, "token-seen")).read().strip()),
      (None, False, ""))
check("update + reinstall toast", s.toasts, ["Updated Med to v2 (the old copy is kept beside it) and ran its installer again"])
check("page rebuilt once, after the installer", s.rebuilt, ["P"])
check("new release no longer offered", s.latest_tags, {})

s, d, path = updated_project('echo "cannot copy to ~/.local/share" >&2; exit 3\n')
check("failed install.sh is reported", s.toasts,
      ['Updated Med to v2, but its install.sh failed: cannot copy to ~/.local/share. '
       'Use "Install again" on its page to see why.'])

s, d, path = updated_project(None)
check("no install.sh: nothing is run", s.ran, [])
check("no install.sh: plain toast", s.toasts, ["Updated Med to v2 (the old copy is kept beside it)"])

s = UpdStub()
s._updated({"id": "P", "name": "Med", "path": folder}, {"tag": "v2"}, False)
check("failed download runs nothing", (s.ran, s.toasts, s.rebuilt), ([], [], ["P"]))

check("reinstall: plain install.sh", g.reinstall_needed("./install.sh"), True)
check("reinstall: software step first, then install.sh", g.reinstall_needed("sudo pacman -S --needed foo && ./install.sh"), True)
check("reinstall: not for npm", g.reinstall_needed("npm install"), False)
check("reinstall: not for nothing", g.reinstall_needed(None), False)

print("ALL OK" if not failed else f"FAILED: {failed}")
sys.exit(1 if failed else 0)
