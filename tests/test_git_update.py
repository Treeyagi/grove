"""Offline checks for updating plain git clones: python3 tests/test_git_update.py"""
import os
import subprocess
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


def git(path, *a):
    subprocess.run(["git", "-C", path, "-c", "user.name=t", "-c", "user.email=t@t", *a], check=True,
                   capture_output=True, text=True)


def commit(path, name):
    with open(os.path.join(path, name), "w") as f:
        f.write(name)
    git(path, "add", name)
    git(path, "commit", "-q", "-m", name)


tmp = tempfile.mkdtemp(prefix="grove-test-")
origin, clone = os.path.join(tmp, "origin"), os.path.join(tmp, "clone")
subprocess.run(["git", "init", "-q", "-b", "main", origin], check=True)
commit(origin, "a")
subprocess.run(["git", "clone", "-q", origin, clone], check=True)

check("not a git folder", g.git_behind_count(tmp), None)
check("up to date", g.git_behind_count(clone), 0)
commit(origin, "b")
commit(origin, "c")
git(clone, "fetch", "-q", "origin")
check("two behind after fetch", g.git_behind_count(clone), 2)
check("fast-forward works", g.git_fast_forward(clone)[0], True)
check("now up to date", g.git_behind_count(clone), 0)

# detached clone (how Grove's own copies are sometimes left) goes back onto main
commit(origin, "d")
git(clone, "fetch", "-q", "origin")
git(clone, "checkout", "-q", "--detach", "HEAD")
ok, msg = g.git_fast_forward(clone)
check("detached clone moves onto main", ok, True)
check("detached now on main", g._git(clone, "symbolic-ref", "--short", "HEAD")[1], "main")

# never loses work
commit(origin, "e")
git(clone, "fetch", "-q", "origin")
with open(os.path.join(clone, "a"), "w") as f:
    f.write("edited")
check("dirty clone refused", g.git_fast_forward(clone)[0], False)
check("dirty file kept", open(os.path.join(clone, "a")).read(), "edited")
git(clone, "checkout", "-q", "--", "a")
git(clone, "checkout", "-q", "-b", "mine")
check("other branch refused", g.git_fast_forward(clone)[0], False)
git(clone, "checkout", "-q", "main")
commit(clone, "local-only")          # clone ahead: diverges from origin's new commit
check("diverged refused", g.git_fast_forward(clone)[0], False)

print("ALL OK" if not failed else f"FAILED: {failed}")
sys.exit(1 if failed else 0)
