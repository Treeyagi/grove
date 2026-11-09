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
      {"tag": "v2", "assets": [{"name": "b", "api": "", "url": "x"}]})
check("rest json: download link, not the API url",
      g.parse_release('{"tag_name":"v2","assets":[{"name":"b","url":"api","browser_download_url":"dl"}]}')["assets"][0]["url"], "dl")
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

# a program with its own --install gets it as the install step
d = os.path.join(tmp, "selfinst")
os.makedirs(d)
open(os.path.join(d, "buddy"), "w").write("#!/bin/sh\n# usage: buddy [--stop | --install | --uninstall]\n")
os.chmod(os.path.join(d, "buddy"), 0o755)
check("--install is picked up", g.detect_commands(d), ("./buddy --install", "./buddy"))

# one without gets an app-menu entry instead
d = os.path.join(tmp, "plain")
os.makedirs(d)
open(os.path.join(d, "plain"), "w").write("#!/bin/sh\n")
os.chmod(os.path.join(d, "plain"), 0o755)
check("plain program: no installer", g.detect_commands(d), ("", "./plain"))
os.environ["XDG_DATA_HOME"] = os.path.join(tmp, "xdg")
entry = g.menu_entry(d, "Plain App", "./plain")
text = open(entry).read()
check("menu entry points at the program", f'Exec="{os.path.join(d, "plain")}"' in text and "Name=Plain App" in text, True)

# a program with --deps and --install: dependencies first, then its install
d = os.path.join(tmp, "withdeps")
os.makedirs(d)
open(os.path.join(d, "buddy"), "w").write("#!/bin/sh\n# buddy [--deps [--yes] | --install | --stop]\n")
os.chmod(os.path.join(d, "buddy"), 0o755)
check("--deps then --install", g.detect_commands(d), ("./buddy --deps --yes && ./buddy --install", "./buddy"))

# a project with its own install-deps.sh (source clone): deps first, then the README's install
d = os.path.join(tmp, "src")
os.makedirs(os.path.join(d, "tools"))
os.makedirs(os.path.join(d, "overlay"))
open(os.path.join(d, "tools", "install-deps.sh"), "w").write("# --yes\n")
open(os.path.join(d, "tools", "install.py"), "w").write("")
open(os.path.join(d, "overlay", "main.py"), "w").write("")
open(os.path.join(d, "README.md"), "w").write("## Install\n```bash\npython3 tools/install.py\n```\n## Run\n```bash\npython3 overlay/main.py\n```\n")
check("source clone: deps, install, run", g.detect_commands(d),
      ("sh tools/install-deps.sh --yes && python3 tools/install.py", "python3 overlay/main.py"))

# self-update
d = tempfile.mkdtemp()
cur = os.path.join(d, "grove.py")
open(cur, "w").write("class Grove: pass\n")
check("update: same file is not an update", g.update_available("class Grove: pass\n", cur), False)
check("update: newer file is", g.update_available("class Grove: pass\nX = 1\n", cur), True)
check("update: broken python is refused", g.update_available("class Grove(:\n", cur), False)
check("update: a page that isn't Grove is refused", g.update_available("print(1)\n", cur), False)
g.write_update("class Grove: pass\nX = 1\n", cur)
check("update: written and runnable", (open(cur).read(), os.access(cur, os.X_OK), os.listdir(d)),
      ("class Grove: pass\nX = 1\n", True, ["grove.py"]))

# sharing with a token
fake = "github_pat_" + "A1b2C3d4E5f6G7h8I9j0K1"
check("token: fine-grained format ok", g.looks_like_token(fake), True)
check("token: classic format ok", g.looks_like_token("ghp_" + "a" * 36), True)
check("token: junk refused", (g.looks_like_token("hello"), g.looks_like_token(""), g.looks_like_token(fake + " extra")), (False, False, False))
d = tempfile.mkdtemp()
p = g.write_curl_auth(fake, os.path.join(d, "sub", "curl-auth"))
check("token: curl config is private and holds the header",
      (oct(os.stat(p).st_mode & 0o777), open(p).read()), ("0o600", f'header = "Authorization: Bearer {fake}"\n'))
check("token: summary", g.summarize_token('{"login":"treeyagi"}', '[{"full_name":"treeyagi/a","private":true},{"full_name":"treeyagi/b","private":false}]'),
      {"login": "treeyagi", "repos": ["treeyagi/a", "treeyagi/b"], "private": 1})
check("token: bad answer gives None", g.summarize_token("nope", "[]"), None)
rel = g.parse_release('{"tagName":"v1","assets":[{"name":"a.zip","url":"https://github.com/o/r/releases/download/v1/a.zip","apiUrl":"https://api.github.com/repos/o/r/releases/assets/9"}]}')
check("release: gh json keeps the API url for private repos", rel["assets"][0]["api"], "https://api.github.com/repos/o/r/releases/assets/9")
rel = g.parse_release('{"tag_name":"v1","assets":[{"name":"a.zip","url":"https://api.github.com/repos/o/r/releases/assets/9","browser_download_url":"https://github.com/o/r/releases/download/v1/a.zip"}]}')
check("release: REST json too", (rel["assets"][0]["api"], rel["assets"][0]["url"]),
      ("https://api.github.com/repos/o/r/releases/assets/9", "https://github.com/o/r/releases/download/v1/a.zip"))

# project icons
d = tempfile.mkdtemp()
g.ICON_DIR_USER, g.ICON_CACHE = os.path.join(d, "user"), os.path.join(d, "cache")
proj = os.path.join(d, "proj"); os.makedirs(proj)
mine = {"name": "Medllm", "path": ""}
built = g.find_icon(mine)
check("icon: built-in one is found by name (any case) and cached", (built is not None and built.startswith(g.ICON_CACHE), open(built).read().startswith("<svg")), (True, True))
check("icon: every built-in is valid SVG text", all(v.startswith("<svg") and v.endswith("</svg>") for v in g.BUILTIN_ICONS.values()), True)
check("icon: unknown project has none", g.find_icon({"name": "nobody-home", "path": ""}), None)
open(os.path.join(proj, "icon.png"), "wb").write(b"x")
check("icon: the project's own icon beats the built-in", g.find_icon({"name": "Medllm", "path": proj}), os.path.join(proj, "icon.png"))
os.makedirs(g.ICON_DIR_USER); open(os.path.join(g.ICON_DIR_USER, "medllm.svg"), "w").write("<svg/>")
check("icon: your own icon in ~/.config/grove/icons beats both", g.find_icon({"name": "Medllm", "path": proj}), os.path.join(g.ICON_DIR_USER, "medllm.svg"))

print("\nALL OK" if not failed else f"\nFAILED: {failed}")
sys.exit(1 if failed else 0)
