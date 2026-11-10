"""Offline checks for gh_ready (gh installed AND signed in): python3 tests/test_gh.py"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import grove as g  # noqa: E402

failed = []


def check(name, got, want):
    good = got == want
    print(("ok   " if good else "FAIL ") + name + ("" if good else f"\n     got  {got!r}\n     want {want!r}"))
    if not good:
        failed.append(name)


real_which, real_run = g.shutil.which, g.subprocess.run
calls = []


def fake_run(rc):
    def run(argv, **kw):
        calls.append(argv)
        return subprocess.CompletedProcess(argv, rc)
    return run


def fresh():
    g._GH_SEEN[0], g._GH_SEEN[1] = 0.0, False
    del calls[:]


try:
    g.shutil.which = lambda n: None
    fresh()
    check("no gh at all: not ready, and gh is never run", (g.gh_ready(), calls), (False, []))
    g.shutil.which = lambda n: "/usr/bin/gh"
    g.subprocess.run = fake_run(1)
    fresh()
    check("gh installed but not signed in: not ready", g.gh_ready(), False)
    g.subprocess.run = fake_run(0)
    fresh()
    check("gh signed in: ready", g.gh_ready(), True)
    check("it asks for github.com only, with gh auth status", calls[0][:3] + calls[0][3:5], ["gh", "auth", "status", "--hostname", "github.com"])
    n = len(calls)
    g.gh_ready()
    check("the answer is remembered (no second gh call)", len(calls), n)
    g._GH_SEEN[0] -= 60
    g.subprocess.run = fake_run(1)
    check("after 30 s it asks again (signed out later)", g.gh_ready(), False)

    def boom(argv, **kw):
        raise OSError("gone")
    g.subprocess.run = boom
    fresh()
    check("gh that can't run counts as not ready", g.gh_ready(), False)
finally:
    g.shutil.which, g.subprocess.run = real_which, real_run

print("\nALL OK" if not failed else f"\n{len(failed)} FAILED: {failed}")
sys.exit(1 if failed else 0)
