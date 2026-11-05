"""Offline checks for release downloads and run detection: python3 tests/test_releases.py"""
import io
import os
import stat
import sys
import tarfile
import tempfile
import zipfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import grove as g  # noqa: E402

failed = []


def check(name, got, want):
    good = got == want
    print(("ok   " if good else "FAIL ") + name + ("" if good else f"\n     got  {got!r}\n     want {want!r}"))
    if not good:
        failed.append(name)


def make_zip(path, files):   # files: {name: (content, mode)}
    with zipfile.ZipFile(path, "w") as z:
        for name, (content, mode) in files.items():
            zi = zipfile.ZipInfo(name)
            zi.external_attr = (stat.S_IFREG | mode) << 16
            z.writestr(zi, content)


tmp = tempfile.mkdtemp()
names = ["a-linux-x86_64.AppImage", "a-linux-x86_64.tar.gz", "a-win64.zip", "a-macos-arm64.dmg",
         "a.tar.gz.sha256", "a_amd64.deb", "a-linux-aarch64.tar.gz", "SHA256SUMS", "setup.run"]
pick = lambda ns: (g.pick_asset([{"name": n, "url": ""} for n in ns]) or {}).get("name")  # noqa: E731
check("AppImage first", pick(names), names[0])
check("then the Linux tarball", pick(names[1:]), names[1])
check("nothing usable", pick(names[2:]), None)
check("rest json", g.parse_release('{"tag_name":"v2","assets":[{"name":"b","browser_download_url":"x"}]}'),
      {"tag": "v2", "assets": [{"name": "b", "url": "x"}]})
check("not json", g.parse_release("nope"), None)

# a folder with a file of the same name inside it (app/app) lifts up cleanly
z = os.path.join(tmp, "a.zip")
make_zip(z, {"app/app": ("#!/bin/sh\n", 0o755), "app/requirements.txt": ("x\n", 0o644)})
d = os.path.join(tmp, "app1")
g.unpack(z, d)
check("app/app lifted", sorted(os.listdir(d)), ["app", "requirements.txt"])
check("binary release: no build step", g.detect_commands(d), ("", "./app"))

# launcher scripts beat a .desktop whose Exec uses $PATH tricks
z = os.path.join(tmp, "b.zip")
make_zip(z, {"bose/run-gui.sh": ("#!/bin/sh\n", 0o755), "bose/install.sh": ("#!/bin/sh\n", 0o755),
             "bose/x.desktop": ("[Desktop Entry]\nExec=sh -c \"cd %k && ./run-gui.sh\"\n", 0o644)})
d = os.path.join(tmp, "bose")
g.unpack(z, d)
check("launcher script + install.sh", g.detect_commands(d), ("./install.sh", "./run-gui.sh"))

# AppImage: copied and made executable
ai = os.path.join(tmp, "Cool-x86_64.AppImage")
open(ai, "w").write("x")
d = os.path.join(tmp, "cool")
g.unpack(ai, d)
check("AppImage run", g.detect_commands(d), ("", "./Cool-x86_64.AppImage"))
check("AppImage executable", os.access(os.path.join(d, "Cool-x86_64.AppImage"), os.X_OK), True)

# a tarball keeps its executable flag
tb = os.path.join(tmp, "u.tar.gz")
with tarfile.open(tb, "w:gz") as t:
    ti = tarfile.TarInfo("Tool-Utility")
    ti.size, ti.mode = 4, 0o755
    t.addfile(ti, io.BytesIO(b"#!sh"))
d = os.path.join(tmp, "tool")
g.unpack(tb, d)
check("tar.gz single program", g.detect_commands(d), ("", "./Tool-Utility"))

# a path that escapes the folder is refused
bad = os.path.join(tmp, "bad.tar.gz")
with tarfile.open(bad, "w:gz") as t:
    ti = tarfile.TarInfo("../evil")
    ti.size = 1
    t.addfile(ti, io.BytesIO(b"x"))
try:
    g.unpack(bad, os.path.join(tmp, "x"))
    check("escaping path refused", "unpacked", "refused")
except OSError:
    check("escaping path refused", "refused", "refused")

# the README says how: install and run blocks, and only for files that exist
proj = os.path.join(tmp, "proj")
os.makedirs(os.path.join(proj, "overlay"))
open(os.path.join(proj, "overlay", "main.py"), "w").write("")
open(os.path.join(proj, "README.md"), "w").write(
    "# P\n\n## One-line install and run\n```bash\ncurl -fsSL https://x/i.sh | sh\n```\n"
    "## Run him\n```bash\npython3 overlay/main.py\n```\n## Install in the menu\n```bash\nsudo make install\n"
    "python3 missing.py\n```\n")
check("README: run found, sudo and missing files refused", g.detect_commands(proj), ("", "python3 overlay/main.py"))

print("\nALL OK" if not failed else f"\nFAILED: {failed}")
sys.exit(1 if failed else 0)
