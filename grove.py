#!/usr/bin/env python3
"""Grove: organise your GitHub projects in a custom tree and launch them."""
import base64
import json
import os
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import time
import uuid
import zipfile

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, GLib, GObject, Gtk  # noqa: E402

APP_ID = "io.github.grove.Launcher"
ICON_NAME = "io.github.grove.Launcher"  # the wizard-tree icon installed by install.sh
CONFIG = os.path.join(GLib.get_user_config_dir(), "grove", "config.json")
CACHE_DIR = os.path.join(GLib.get_user_cache_dir(), "grove", "readmes")
INBOX = "Unsorted"
FEATURED = "Treeyagi"  # always synced and pinned first, for everyone
USERNAME = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})")

# argv inserted between the terminal executable and the command to run
TERMINAL_FLAGS = {
    "alacritty": ["-e"],
    "konsole": ["-e"],
    "xterm": ["-e"],
    "kitty": [],
    "foot": [],
    "gnome-terminal": ["--"],
    "wezterm": ["start", "--cwd", "{path}", "--"],
}


BANNER = """ ██████╗ ██████╗  ██████╗ ██╗   ██╗███████╗
██╔════╝ ██╔══██╗██╔═══██╗██║   ██║██╔════╝
██║  ███╗██████╔╝██║   ██║██║   ██║█████╗
██║   ██║██╔══██╗██║   ██║╚██╗ ██╔╝██╔══╝
╚██████╔╝██║  ██║╚██████╔╝ ╚████╔╝ ███████╗
 ╚═════╝ ╚═╝  ╚═╝ ╚═════╝   ╚═══╝  ╚══════╝"""

# Neon on black: green text, cyan chrome, magenta for selection and primary actions.
HACKERS_CSS = """
window.hackers {
  background-color: #05060a; color: #00ff9c;
  font-family: "JetBrains Mono", "Fira Code", "DejaVu Sans Mono", monospace;
  background-image: linear-gradient(to bottom, rgba(0,255,156,0.05) 50%, transparent 50%);
  background-size: 100% 4px;
}
window.hackers headerbar {
  background: #080a12; color: #00e5ff; border-bottom: 1px solid #00e5ff;
  box-shadow: 0 0 14px rgba(0,229,255,0.35);
}
window.hackers headerbar windowtitle .title, window.hackers headerbar label { color: #00e5ff; }
window.hackers toolbarview, window.hackers scrolledwindow, window.hackers listview,
window.hackers preferencespage, window.hackers .navigation-sidebar { background: transparent; }
window.hackers label, window.hackers .title, window.hackers .heading { color: #00ff9c; }
window.hackers .dim-label, window.hackers .subtitle { color: #1fb67a; opacity: 1; }
window.hackers .banner { color: #ff2bd6; text-shadow: 0 0 10px rgba(255,43,214,0.8); font-size: 13px; }
window.hackers .tagline { color: #00e5ff; letter-spacing: 3px; }
window.hackers .sidebar-pane, window.hackers .content-pane, window.hackers navigation-view,
window.hackers .view { background-color: transparent; }
window.hackers .sidebar-pane { background-color: rgba(0,229,255,0.04); border-right: 1px solid rgba(0,229,255,0.4); }
window.hackers listview row { border-radius: 0; }
window.hackers listview row:hover { background: rgba(0,229,255,0.10); }
window.hackers listview row:selected {
  background: rgba(255,43,214,0.18); box-shadow: inset 3px 0 #ff2bd6;
}
window.hackers listview row:selected label { color: #ff2bd6; text-shadow: 0 0 6px rgba(255,43,214,0.7); }
window.hackers button {
  background: transparent; background-image: none; color: #00e5ff; box-shadow: none;
  border: 1px solid #00e5ff; border-radius: 0;
}
window.hackers button:hover { background: rgba(0,229,255,0.15); box-shadow: 0 0 10px rgba(0,229,255,0.6); }
window.hackers button.flat { border-color: transparent; }
window.hackers button.suggested-action { background: #ff2bd6; color: #05060a; border-color: #ff2bd6; }
window.hackers button.suggested-action:hover { box-shadow: 0 0 14px rgba(255,43,214,0.9); }
window.hackers button.destructive-action { color: #ff3b3b; border-color: #ff3b3b; }
window.hackers button.destructive-action:hover { background: rgba(255,59,59,0.15); box-shadow: 0 0 10px rgba(255,59,59,0.6); }
window.hackers button label, window.hackers button image { color: inherit; }
window.hackers list.boxed-list, window.hackers .boxed-list {
  background: rgba(0,255,156,0.04); border: 1px solid rgba(0,255,156,0.4); border-radius: 0; box-shadow: none;
}
window.hackers row { background: transparent; }
window.hackers row.entry:focus-within { box-shadow: inset 0 0 0 1px #ff2bd6; }
window.hackers entry, window.hackers text { color: #00ff9c; caret-color: #ff2bd6; background: transparent; }
window.hackers preferencesgroup > box > box > label.heading { color: #ff2bd6; letter-spacing: 2px; }
window.hackers .card { background: rgba(0,255,156,0.05); border: 1px solid rgba(0,255,156,0.4);
  border-radius: 0; box-shadow: none; }
window.hackers .title-2 { color: #ff2bd6; text-shadow: 0 0 8px rgba(255,43,214,0.6); }
window.hackers textview, window.hackers textview text { background: transparent; color: #00ff9c; }
window.hackers searchentry { border: 1px solid rgba(0,229,255,0.5); border-radius: 0; }
window.hackers row.expander { background: transparent; }
window.hackers .readme { background-color: #05060a; }
window.hackers toast { background: #080a12; color: #00ff9c; border: 1px solid #00ff9c; border-radius: 0; }
window.hackers scrollbar slider { background: #00e5ff; border-radius: 0; }
"""


def detect(candidates, default):
    return next((c for c in candidates if shutil.which(c)), default)


def default_settings():
    return {
        "editor": detect(["code", "codium", "zed", "kate", "gedit"], "xdg-open"),
        "terminal": detect(list(TERMINAL_FLAGS), "xterm"),
        "projects_dir": os.path.expanduser("~/Projects"),
        "hackers": True,
        "extra_users": [],     # other GitHub accounts whose public repos to follow
        "public_only": False,  # never import private repos
        "prefer_releases": True,  # Install and Run download a repo's latest release when it has one
    }


def new_id():
    return uuid.uuid4().hex[:12]


def new_group(name):
    return {"type": "group", "id": new_id(), "name": name, "children": []}


def new_project(name, **kw):
    return {"type": "project", "id": new_id(), "name": name, "url": "",
            "description": "", "path": "", "install": "", "run": "", "site": "", "private": False, **kw}


def walk(items, parent=None):
    """Yield (node, siblings, parent_group) for every node under items."""
    for d in list(items):
        yield d, items, parent
        if d["type"] == "group":
            yield from walk(d["children"], d)


def _detect_by_files(path):
    """Guess (install, run) shell commands from the build files in a project."""
    def has(*names):
        return any(os.path.exists(os.path.join(path, n)) for n in names)

    def makefile_target(t):
        try:
            with open(os.path.join(path, "Makefile")) as f:
                return any(line.startswith(t + ":") for line in f)
        except OSError:
            return False

    if has("install.sh"):
        return "./install.sh", ""
    if has("package.json"):
        try:
            with open(os.path.join(path, "package.json")) as f:
                scripts = json.load(f).get("scripts", {})
        except (OSError, ValueError):
            scripts = {}
        run = "npm start" if "start" in scripts else "npm run dev" if "dev" in scripts else ""
        return "npm install", run
    if has("Cargo.toml"):
        return "cargo build --release", "cargo run --release"
    if has("go.mod"):
        return "go build ./...", "go run ."
    if has("PKGBUILD"):
        return "makepkg -si", ""
    if has("requirements.txt", "pyproject.toml", "setup.py"):
        dep = "-r requirements.txt" if has("requirements.txt") else "-e ."
        entry = next((n for n in ("main.py", "app.py", "__main__.py") if has(n)), None)
        return (f"python3 -m venv .venv && .venv/bin/pip install {dep}",
                f".venv/bin/python {entry}" if entry else "")
    if has("Makefile"):
        return "make", "make run" if makefile_target("run") else ""
    return "", ""



# ---- releases -------------------------------------------------------------------------------
# Worst first: things that are not for a Linux PC, and files that are not the program.
NOT_FOR_US = re.compile(r"(?i)(mac|darwin|osx|\.exe|\.msi|\.dmg|\.deb|\.rpm|\.apk|\.sig|\.asc|\.sha|\.md5|\.txt|\.json"
                        r"|\.sbom|checksum|sums|sha\d+|arm64|aarch64|armv|i386|i686|riscv|ppc|s390|(?<![a-z])win(dows|32|64)?(?![a-z]))")


def asset_score(name):
    """How good a release file looks for this PC (x86_64 Linux); 0 or less means skip it."""
    n = name.lower()
    if NOT_FOR_US.search(n) or n.endswith(".pkg.tar.zst"):
        return 0
    score = 1
    if n.endswith(".appimage"):
        score += 50
    elif n.endswith((".tar.gz", ".tgz", ".tar.xz", ".tar.bz2")):
        score += 30
    elif n.endswith(".zip"):
        score += 25
    elif "." in os.path.basename(n) or not re.search(r"linux|x86[_-]64|amd64", n):
        return 0   # some other kind of file (a bare name only counts if it says it's for Linux)
    if re.search(r"x86[_-]64|amd64|x64", n):
        score += 10
    if "linux" in n:
        score += 10
    return score


def pick_asset(assets):
    """The best release file for this PC, as {name, url}, or None (then Grove clones the release's source)."""
    ranked = sorted(((asset_score(a["name"]), a) for a in assets), key=lambda t: -t[0])
    return ranked[0][1] if ranked and ranked[0][0] > 0 else None


def parse_release(text):
    """Normalise `gh release view --json` or the REST API's JSON into {tag, assets:[{name,url}]}, or None."""
    try:
        r = json.loads(text)
    except ValueError:
        return None
    tag = r.get("tagName") or r.get("tag_name")
    if not tag:
        return None
    assets = [{"name": a.get("name", ""), "url": a.get("url") or a.get("browser_download_url", "")}
              for a in r.get("assets", [])]
    return {"tag": tag, "assets": assets}


def unpack(archive, dest):
    """Put a downloaded release into dest: AppImages are copied and made runnable, archives are extracted
    (keeping their executable flags), and a lone top-level folder is lifted up so dest holds the app directly."""
    os.makedirs(dest, exist_ok=True)
    real = os.path.realpath(dest)
    if archive.lower().endswith(".appimage") or not (tarfile.is_tarfile(archive) or zipfile.is_zipfile(archive)):
        out = os.path.join(dest, os.path.basename(archive))
        shutil.copy2(archive, out)
        os.chmod(out, 0o755)
        return
    if tarfile.is_tarfile(archive):
        with tarfile.open(archive) as t:
            for m in t.getmembers():
                if not os.path.realpath(os.path.join(dest, m.name)).startswith(real):
                    raise OSError(f"unsafe path in archive: {m.name}")
            t.extractall(dest, filter="data") if hasattr(tarfile, "data_filter") else t.extractall(dest)
    else:
        with zipfile.ZipFile(archive) as z:
            for i in z.infolist():
                target = os.path.realpath(os.path.join(dest, i.filename))
                if not target.startswith(real):
                    raise OSError(f"unsafe path in archive: {i.filename}")
                z.extract(i, dest)
                mode = i.external_attr >> 16
                if mode and not i.is_dir():
                    os.chmod(target, mode & 0o777 | 0o200)
    entries = [e for e in os.listdir(dest) if not e.startswith(".")]
    if len(entries) == 1 and os.path.isdir(os.path.join(dest, entries[0])):
        inner = os.path.join(dest, entries[0])
        aside = os.path.join(dest, f".grove-lift-{os.getpid()}")   # the folder may hold something with its own name
        os.rename(inner, aside)
        for e in os.listdir(aside):
            shutil.move(os.path.join(aside, e), os.path.join(dest, e))
        os.rmdir(aside)


def _is_exec(path):
    return os.path.isfile(path) and os.access(path, os.X_OK)


def release_run(path):
    """The run command for a downloaded release: an AppImage, a launcher script, the one program in the folder,
    or the Exec line of a .desktop file. Empty if nothing obvious is there."""
    try:
        names = sorted(os.listdir(path))
    except OSError:
        return ""
    for n in names:
        if n.lower().endswith(".appimage") and os.path.isfile(os.path.join(path, n)):
            return "./" + shlex.quote(n)
    base = os.path.basename(os.path.normpath(path)).lower()
    launchers = [n for n in names if re.fullmatch(r"(?i)(run|start|launch)([-_.][a-z0-9_.-]*)?\.sh", n) or n == base + ".sh"]
    for n in sorted(launchers, key=lambda n: (n.lower() not in ("run.sh", "start.sh", "launch.sh"), n)):
        if _is_exec(os.path.join(path, n)):
            return "./" + shlex.quote(n)
    skip = re.compile(r"(?i)(install|uninstall|setup|configure|update|\.so|\.sh$|\.py$|\.txt$|\.md$|license)")
    progs = [n for n in names if _is_exec(os.path.join(path, n)) and not skip.search(n)]
    if len(progs) > 1:
        progs = [n for n in progs if n.lower().startswith(base)] or progs[:0]
    if len(progs) == 1:
        return "./" + shlex.quote(progs[0])
    for n in names:
        if n.endswith(".desktop"):
            try:
                with open(os.path.join(path, n), errors="replace") as f:
                    for line in f:
                        if line.startswith("Exec=") and "%k" not in line and "sh -c" not in line:
                            cmd = re.sub(r"\s%[a-zA-Z]", "", line[5:].strip()).strip()
                            first = shlex.split(cmd)[0] if cmd else ""
                            if first and os.path.isabs(first):
                                return cmd
                            if first and os.path.exists(os.path.join(path, first)):
                                return "./" + cmd   # a program in this folder, not one from $PATH
            except (OSError, ValueError):
                pass
    return ""


_RUNNERS = ("python3", "python", "./", "npm ", "npx ", "pnpm ", "yarn ", "cargo ", "go ", "node ", "bun ", "deno ",
            "make", "java ", "flatpak run", "uv run", "poetry run", "ruby ", "bash ", "sh ", ".venv/")
_UNSAFE = re.compile(r"(?i)(sudo|curl|wget|\|\s*(ba)?sh|\brm\b|pacman|\bapt\b|dnf|yay|paru|pip3? install|git clone|\bcd\b|&&|;)")


def _first_command(block, path):
    """The first line of a code block that looks like a safe program start whose files exist."""
    for line in block:
        cmd = re.sub(r"\s+#.*$", "", line.strip().lstrip("$").strip())
        if not cmd or cmd.startswith("#") or _UNSAFE.search(cmd):
            continue
        if not cmd.startswith(_RUNNERS):
            continue
        try:
            parts = shlex.split(cmd)
        except ValueError:
            continue
        files = [t for t in parts[1:] if t.endswith((".py", ".sh", ".js", ".jar"))] + ([parts[0]] if parts[0].startswith("./") else [])
        if all(os.path.exists(os.path.join(path, t)) for t in files):
            return cmd
    return ""


def readme_commands(path):
    """(install, run) from the README: the first safe command in a code block under a heading about installing
    or running, checked against the files that are really there. How the author says to start it."""
    text = ""
    for n in ("README.md", "README", "readme.md", "README.rst", "README.txt"):
        try:
            with open(os.path.join(path, n), errors="replace") as f:
                text = f.read(200_000)
            break
        except OSError:
            pass
    install = run = ""
    heading, block, inside = "", [], False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            if inside:
                cmd = _first_command(block, path)
                if cmd:
                    if re.search(r"(?i)\b(install|setup|set up|build|requirements|dependencies)", heading):
                        install = install or cmd
                    elif re.search(r"(?i)\b(run|running|launch|start|usage|use|quick ?start|getting started)\b", heading):
                        run = run or cmd
            block, inside = [], not inside
        elif inside:
            block.append(line)
        elif line.startswith("#"):
            heading = line.lstrip("#").strip()
    return install, run


def _own_install(path, run):
    """'./app --install' when the program says it has an --install option in its first few KB (a shell stub
    or script does; a big binary won't). Empty otherwise."""
    try:
        with open(os.path.join(path, shlex.split(run)[0]), "rb") as f:
            head = f.read(4096)
    except (OSError, ValueError, IndexError):
        return ""
    return f"{run} --install" if b"--install" in head else ""


def _deps_step(path, run):
    """A command that installs what the project needs before it is installed or run: the program's own
    `--deps` option, or an install-deps.sh in the folder. Adds --yes when the script says it understands it."""
    def head(rel):
        try:
            with open(os.path.join(path, rel), "rb") as f:
                return f.read(8192)
        except OSError:
            return b""
    if run.startswith("./") and " " not in run:
        h = head(shlex.split(run)[0])
        if b"--deps" in h:
            return f"{run} --deps" + (" --yes" if b"--yes" in h else "")
    for rel in ("install-deps.sh", "tools/install-deps.sh", "scripts/install-deps.sh"):
        if os.path.isfile(os.path.join(path, rel)):
            return f"sh {shlex.quote(rel)}" + (" --yes" if b"--yes" in head(rel) else "")
    return ""


def menu_entry(path, name, run):
    """Write an app-menu entry for a downloaded program (run like './app'); returns its path or raises OSError."""
    parts = shlex.split(run)
    exe = os.path.abspath(os.path.join(path, parts[0]))
    if len(parts) != 1 or not os.access(exe, os.X_OK):
        raise OSError("this project's run command isn't a single program")
    icon = next((os.path.join(path, f) for f in sorted(os.listdir(path))
                 if re.match(r"(?i)(icon|logo|[a-z0-9_-]*)\.(png|svg)$", f)), "")
    apps = os.path.join(GLib.get_user_data_dir(), "applications")
    os.makedirs(apps, exist_ok=True)
    out = os.path.join(apps, "grove-" + re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") + ".desktop")
    quoted = '"' + exe.replace('\\', '\\\\').replace('"', '\\"') + '"'
    lines = ["[Desktop Entry]", "Type=Application", f"Name={name}", f"Comment={name} (added by Grove)",
             f"Exec={quoted}", f"Path={path}", "Terminal=false", "Categories=Utility;"]
    if icon:
        lines.append(f"Icon={icon}")
    with open(out, "w") as f:
        f.write("\n".join(lines) + "\n")
    return out


def detect_commands(path):
    """Guess (install, run) shell commands for a project: its build files first, then what a downloaded release
    contains (AppImage, launcher, program), then what the README says, then a script named like the project."""
    install, run = _detect_by_files(path)
    if not run:
        run = release_run(path)
        if run and install != "./install.sh":
            install = ""   # a ready-to-run program doesn't need building
    if not (install and run):
        r_install, r_run = readme_commands(path)
        install, run = install or r_install, run or r_run
    if run.startswith("./") and not install and " " not in run:
        install = _own_install(path, run)
    deps = _deps_step(path, run)
    if deps:   # needed software first, then the install step, then (Grove adds) the run
        install = f"{deps} && {install}" if install else deps
    if not run:
        name = os.path.basename(os.path.normpath(path)).lower()
        if os.path.isfile(os.path.join(path, name + ".py")):
            run = f"python3 {shlex.quote(name + '.py')}"
    return install, run


def spawn(argv, cwd=None):
    """Start a detached process; return an error string or None."""
    try:
        subprocess.Popen(argv, cwd=cwd, start_new_session=True,
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
    except OSError as e:
        return f"{argv[0]}: {e.strerror or e}"
    return None


def repo_slug(url):
    m = re.match(r"https?://github\.com/([^/]+/[^/#?]+?)(?:\.git)?/?$", url or "")
    return m.group(1) if m else None


def pages_url(url):
    """Where a repo's GitHub Pages site would live (owner.github.io/repo/)."""
    slug = repo_slug(url)
    if not slug:
        return None
    owner, repo = slug.split("/")
    host = f"{owner.lower()}.github.io"
    return f"https://{host}/" if repo.lower() == host else f"https://{host}/{repo}/"


def clean_inline(t):
    t = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", t)
    t = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", t)
    t = re.sub(r"<[^>]+>", "", t)
    t = re.sub(r"(\*\*|__)(.+?)\1", r"\2", t)
    t = re.sub(r"`([^`]*)`", r"\1", t)
    return t.strip()


def summarize(md):
    """Pull a plain-language blurb and a few highlight bullets out of a README."""
    md = re.sub(r"<!--.*?-->", "", md, flags=re.S)
    summary, bullets, para, in_code, closed, wanted = "", [], [], False, False, False
    feature_heading = re.compile(r"feature|what (it|you|this)|highlight|overview|about|can do", re.I)
    skip = re.compile(r"(#|\||>|[-*+]\s|\d+[.)]\s|<|!\[|\[!\[|-{3}|={3})")
    for raw in md.splitlines() + [""]:
        line = raw.strip()
        if line.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        if line and not skip.match(line):
            para.append(clean_inline(line))
            continue
        text = " ".join(p for p in para if p)
        para = []
        if len(text) >= 40 and not summary:
            summary = text
            wanted = wanted or text.endswith(":")  # "It has:" introduces the list that follows
        if line.startswith("#"):
            wanted = bool(feature_heading.search(line))
            closed = closed or bool(bullets)
        m = re.match(r"[-*+]\s+(.*)", line)
        if m and summary and wanted and not closed and len(bullets) < 6:
            item = clean_inline(m.group(1))
            if 8 <= len(item) <= 110:
                bullets.append(item)
    if len(summary) > 320:
        cut = summary[:320]
        summary = (cut[:cut.rfind(". ") + 1] if ". " in cut[120:] else cut.rstrip() + "…")
    return summary, bullets


def render_markdown(buf, md):
    """Very small markdown-to-TextBuffer renderer: headings, code, lists, plain links."""
    buf.create_tag("h1", scale=1.6, weight=700)
    buf.create_tag("h2", scale=1.3, weight=700)
    buf.create_tag("h3", scale=1.1, weight=700)
    buf.create_tag("code", family="monospace", scale=0.95)
    md = re.sub(r"<!--.*?-->", "", md, flags=re.S)
    in_code, pending = False, ""

    def flush():
        nonlocal pending
        if pending:
            buf.insert(buf.get_end_iter(), pending + "\n")
            pending = ""

    for raw in md.splitlines():
        if raw.strip().startswith("```"):
            flush()
            in_code = not in_code
            continue
        if in_code or raw.lstrip().startswith("|"):
            flush()
            buf.insert_with_tags_by_name(buf.get_end_iter(), raw + "\n", "code")
            continue
        m = re.match(r"(#{1,6})\s+(.*)", raw.strip())
        if m:
            flush()
            tag = f"h{min(len(m.group(1)), 3)}"
            buf.insert_with_tags_by_name(buf.get_end_iter(), clean_inline(m.group(2)) + "\n", tag)
        elif re.match(r"\s*[-*+]\s", raw):
            flush()
            pending = re.match(r"\s*", raw).group(0) + "• " + clean_inline(re.sub(r"^\s*[-*+]\s+", "", raw))
        elif raw.strip():
            # soft-wrapped line: join it onto the paragraph or list item above
            pending = (pending + " " if pending else "") + clean_inline(raw)
        else:
            flush()
            buf.insert(buf.get_end_iter(), "\n")
    flush()


class Node(GObject.Object):
    title = GObject.Property(type=str, default="")
    subtitle = GObject.Property(type=str, default="")

    def __init__(self, data, kids=None, subtitle=""):
        super().__init__(title=data["name"], subtitle=subtitle)
        self.data = data
        self.kids = kids
        self.is_group = data["type"] == "group"


def build_store(items, blurb=lambda d: ""):
    store = Gio.ListStore(item_type=Node)
    for d in sorted(items, key=lambda d: (d["type"] != "group", not d.get("pinned"), d["name"].lower())):
        if d["type"] == "group":
            store.append(Node(d, build_store(d["children"], blurb)))
        else:
            store.append(Node(d, None, blurb(d)))
    return store


class Grove(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="Grove", default_width=1000, default_height=680)
        self.load()
        self.update_checked = set()   # projects already asked about a newer release this session
        self.latest_tags = {}         # project id -> the newer release found
        self.sel = None
        self.expanded = set(self.data.get("expanded", []))
        self.query = ""
        self.readmes = {}        # project id -> README text ("" = repo has none)
        self.fetching = {}       # project id -> callbacks, for README downloads in flight

        self.toasts = Adw.ToastOverlay()
        self.set_content(self.toasts)
        split = Adw.NavigationSplitView(min_sidebar_width=280, max_sidebar_width=380)
        self.toasts.set_child(split)

        # sidebar
        header = Adw.HeaderBar()
        sync = Gtk.Button(icon_name="view-refresh-symbolic", tooltip_text="Sync repos from GitHub")
        sync.connect("clicked", lambda *_: self.sync())
        add_proj = Gtk.Button(icon_name="list-add-symbolic", tooltip_text="Add project")
        add_proj.connect("clicked", lambda *_: self.add_project())
        add_grp = Gtk.Button(icon_name="folder-new-symbolic", tooltip_text="New group")
        add_grp.connect("clicked", lambda *_: self.add_group())
        header.pack_start(sync)
        header.pack_start(add_proj)
        header.pack_start(add_grp)
        menu = Gio.Menu()
        menu.append("Re-read all READMEs", "win.readmes")
        menu.append("Bring back removed repos", "win.restore")
        menu.append("Hackers theme", "win.hackers")
        menu.append("Settings", "win.settings")
        header.pack_end(Gtk.MenuButton(icon_name="open-menu-symbolic", menu_model=menu))
        act = Gio.SimpleAction.new("settings", None)
        act.connect("activate", lambda *_: self.show_settings())
        self.add_action(act)
        restore = Gio.SimpleAction.new("restore", None)
        restore.connect("activate", lambda *_: self.restore_removed())
        self.add_action(restore)
        reread = Gio.SimpleAction.new("readmes", None)
        reread.connect("activate", lambda *_: self.prefetch_readmes(force=True))
        self.add_action(reread)
        theme = Gio.SimpleAction.new_stateful(
            "hackers", None, GLib.Variant.new_boolean(self.settings["hackers"]))
        theme.connect("change-state", self._toggle_hackers)
        self.add_action(theme)

        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", self._row_setup)
        factory.connect("bind", self._row_bind)
        factory.connect("unbind", self._row_unbind)
        self.view = Gtk.ListView(factory=factory, css_classes=["navigation-sidebar"])
        self.view.connect("activate", self._row_activated)
        side = Adw.ToolbarView(content=Gtk.ScrolledWindow(child=self.view))
        side.add_top_bar(header)
        self.search = Gtk.SearchEntry(placeholder_text="Search projects…", margin_start=8,
                                      margin_end=8, margin_bottom=8)
        self.search.connect("search-changed", self._on_search)
        side.add_top_bar(self.search)
        bottom = Gtk.ActionBar()
        rm_btn = Gtk.Button(icon_name="user-trash-symbolic", tooltip_text="Remove the selected repo or group (Delete)",
                            css_classes=["flat"])
        rm_btn.connect("clicked", lambda *_: self.remove_selected())
        bottom.pack_start(rm_btn)
        side.add_bottom_bar(bottom)
        keys = Gtk.ShortcutController()
        keys.add_shortcut(Gtk.Shortcut.new(Gtk.ShortcutTrigger.parse_string("Delete"),
                                           Gtk.CallbackAction.new(lambda *_: self.remove_selected() or True)))
        self.view.add_controller(keys)
        self.side_page = Adw.NavigationPage(title="Projects", child=side)
        split.set_sidebar(self.side_page)

        # content
        self.detail = Adw.Bin()
        content = Adw.ToolbarView(content=self.detail)
        content.add_top_bar(Adw.HeaderBar())
        self.content_page = Adw.NavigationPage(title="Details", child=content)
        split.set_content(self.content_page)

        self.connect("close-request", self._on_close)
        self.load_css()
        self.apply_theme()
        self.rebuild()
        GLib.idle_add(self.auto_sync)
        GLib.idle_add(self.prefetch_readmes)
        GLib.idle_add(self.check_all_sites)

    def _on_search(self, entry):
        self.query = entry.get_text().strip().lower()
        self.rebuild()

    # ---- theme -------------------------------------------------------
    _css_loaded = False

    def load_css(self):
        if Grove._css_loaded:
            return
        provider = Gtk.CssProvider()
        provider.load_from_string(HACKERS_CSS) if hasattr(provider, "load_from_string") \
            else provider.load_from_data(HACKERS_CSS.encode())
        Gtk.StyleContext.add_provider_for_display(
            self.get_display(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        Grove._css_loaded = True

    def logo(self, size):
        """The wizard-tree logo: from the installed icon, or grove.svg next to this script."""
        if Gtk.IconTheme.get_for_display(self.get_display()).has_icon(ICON_NAME):
            return Gtk.Image(icon_name=ICON_NAME, pixel_size=size)
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "grove.svg")
        if os.path.exists(path):
            pic = Gtk.Picture.new_for_filename(path)
            pic.set_size_request(size, size)
            pic.set_can_shrink(False)
            return pic
        return None

    def T(self, text):
        return text.upper() if self.settings["hackers"] else text

    def apply_theme(self):
        on = self.settings["hackers"]
        (self.add_css_class if on else self.remove_css_class)("hackers")
        Adw.StyleManager.get_default().set_color_scheme(
            Adw.ColorScheme.FORCE_DARK if on else Adw.ColorScheme.DEFAULT)
        self.set_title("GROVE // HACK THE PLANET" if on else "Grove")
        self.side_page.set_title("TARGETS" if on else "Projects")
        self.content_page.set_title("PAYLOAD" if on else "Details")
        if self.detail.get_child():
            self.show_detail()

    def _toggle_hackers(self, action, value):
        action.set_state(value)
        self.settings["hackers"] = value.get_boolean()
        self.save()
        self.apply_theme()

    # ---- persistence -------------------------------------------------
    def load(self):
        try:
            with open(CONFIG) as f:
                self.data = json.load(f)
        except (OSError, ValueError):
            self.data = {}
        self.data.setdefault("tree", [])
        self.data["settings"] = {**default_settings(), **self.data.get("settings", {})}
        old = self.data["settings"].pop("github_user", "")
        if old and old not in self.data["settings"]["extra_users"]:
            self.data["settings"]["extra_users"].append(old)

    def save(self):
        self.data["expanded"] = sorted(self.expanded)
        os.makedirs(os.path.dirname(CONFIG), exist_ok=True)
        tmp = CONFIG + ".tmp"
        with open(tmp, "w") as f:
            json.dump(self.data, f, indent=2)
        os.replace(tmp, CONFIG)

    def _on_close(self, *_):
        self.snapshot_expanded()
        self.save()
        return False

    @property
    def settings(self):
        return self.data["settings"]

    @property
    def tree(self):
        return self.data["tree"]

    def toast(self, msg):
        self.toasts.add_toast(Adw.Toast(title=msg, timeout=4))

    # ---- tree model --------------------------------------------------
    def find(self, nid):
        for d, sibs, parent in walk(self.tree):
            if d["id"] == nid:
                return d, sibs, parent
        return None, None, None

    def snapshot_expanded(self):
        if not self.sel:
            return
        model = self.sel.get_model()
        for i in range(model.get_n_items()):
            row = model.get_item(i)
            data = row.get_item().data
            if data["type"] == "group":
                (self.expanded.add if row.get_expanded() else self.expanded.discard)(data["id"])

    def current(self):
        row = self.sel.get_selected_item() if self.sel else None
        return row.get_item() if row else None

    def rebuild(self, select=None):
        self.snapshot_expanded()
        cur = self.current()
        select = select or (cur.data["id"] if cur else None)
        _, _, parent = self.find(select) if select else (None, None, None)
        while parent:
            self.expanded.add(parent["id"])
            _, _, parent = self.find(parent["id"])

        root = self.search_store() if self.query else build_store(self.tree, self.blurb)
        model = Gtk.TreeListModel.new(root, False, False, lambda n: n.kids)
        i = 0
        while i < model.get_n_items():
            row = model.get_item(i)
            if row.get_item().data["id"] in self.expanded:
                row.set_expanded(True)
            i += 1
        self.sel = Gtk.SingleSelection(model=model, autoselect=False, can_unselect=True)
        pos = next((i for i in range(model.get_n_items())
                    if model.get_item(i).get_item().data["id"] == select), Gtk.INVALID_LIST_POSITION)
        self.sel.set_selected(pos)
        self.sel.connect("notify::selected", lambda *_: self.show_detail())
        self.view.set_model(self.sel)
        self.show_detail()
        self.save()

    def _row_setup(self, _f, item):
        box = Gtk.Box(spacing=8)
        box.icon = Gtk.Image()
        box.label = Gtk.Label(xalign=0, ellipsize=3)
        box.sub = Gtk.Label(xalign=0, ellipsize=3, css_classes=["dim-label", "caption"])
        text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, valign=Gtk.Align.CENTER)
        text.append(box.label)
        text.append(box.sub)
        box.lock = Gtk.Image(icon_name="changes-prevent-symbolic", css_classes=["dim-label"],
                             tooltip_text="Private repository")
        box.badge = Gtk.Label(css_classes=["dim-label", "caption"])
        for w in (box.icon, text, box.lock, box.badge):
            box.append(w)
        item.set_child(Gtk.TreeExpander(child=box))

    def _row_bind(self, _f, item):
        row, exp = item.get_item(), item.get_child()
        node, box = row.get_item(), exp.get_child()
        exp.set_list_row(row)
        d = node.data
        box.icon.set_from_icon_name("folder-symbolic" if node.is_group else "text-x-script-symbolic")
        box.lock.set_visible(bool(d.get("private")))
        if node.is_group:
            box.badge.set_label(str(sum(1 for c, *_ in walk(d["children"]) if c["type"] == "project")))
        else:
            cloned = os.path.isdir(os.path.expanduser(d["path"])) if d["path"] else False
            box.badge.set_label("●" if cloned else "")
            box.badge.set_tooltip_text("Cloned locally" if cloned else None)
        box.binding = node.bind_property("title", box.label, "label", GObject.BindingFlags.SYNC_CREATE)
        box.sub_binding = node.bind_property("subtitle", box.sub, "label", GObject.BindingFlags.SYNC_CREATE)
        box.sub.set_visible(not node.is_group)

    def _row_unbind(self, _f, item):
        box = item.get_child().get_child()
        for name in ("binding", "sub_binding"):
            if getattr(box, name, None):
                getattr(box, name).unbind()
                setattr(box, name, None)

    def _row_activated(self, _view, pos):
        node = self.sel.get_item(pos).get_item()
        if not node.is_group:
            self.open_editor(node.data)

    # ---- detail pane -------------------------------------------------
    def show_detail(self):
        node = self.current()
        if node is None:
            hack = self.settings["hackers"]
            page = Adw.StatusPage(
                title="ACCESS GRANTED" if hack else "Grove",
                description="Select a target from the tree, or jack into GitHub to pull your repos."
                if hack else "Pull in your GitHub repos, sort them into groups, "
                             "and open or run them with one click.")
            if hack:
                page.set_paintable(None)
                box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16, halign=Gtk.Align.CENTER)
                logo = self.logo(112)
                if logo:
                    box.append(logo)
                box.append(Gtk.Label(label=BANNER, css_classes=["banner"], selectable=False))
                box.append(Gtk.Label(label="H A C K   T H E   P L A N E T", css_classes=["tagline"]))
                page.set_child(box)
                parent = box
            else:
                page.set_icon_name(ICON_NAME if Gtk.IconTheme.get_for_display(self.get_display()).has_icon(ICON_NAME)
                                   else "folder-symbolic")
                parent = Gtk.Box(halign=Gtk.Align.CENTER)
                page.set_child(parent)
            btn = Gtk.Button(label=self.T("Sync from GitHub"), halign=Gtk.Align.CENTER,
                             css_classes=["suggested-action", "pill"])
            btn.connect("clicked", lambda *_: self.sync())
            parent.append(btn)
        elif node.is_group:
            page = self.group_page(node)
        else:
            page = self.project_page(node)
        self.detail.set_child(page)

    def entry(self, title, d, key, node=None):
        row = Adw.EntryRow(title=title, text=d.get(key, ""))

        def changed(r):
            d[key] = r.get_text()
            if key == "name" and node:
                node.props.title = d[key] or "Untitled"
            self.save()
        row.connect("changed", changed)
        return row

    def parent_combo(self, d):
        opts = [("Top level", None)] + self.group_options(d["id"])
        _, _, parent = self.find(d["id"])
        combo = Adw.ComboRow(title="Group", model=Gtk.StringList.new([o[0] for o in opts]))
        combo.set_selected(next((i for i, o in enumerate(opts) if o[1] == (parent["id"] if parent else None)), 0))

        def moved(c, _p):
            target = opts[c.get_selected()][1]
            _, sibs, cur = self.find(d["id"])
            if target == (cur["id"] if cur else None):
                return
            sibs.remove(d)
            (self.tree if target is None else self.find(target)[0]["children"]).append(d)
            GLib.idle_add(self.rebuild, d["id"])
        combo.connect("notify::selected", moved)
        return combo

    def group_options(self, exclude, items=None, prefix=""):
        out = []
        for d in sorted(self.tree if items is None else items, key=lambda d: d["name"].lower()):
            if d["type"] != "group" or d["id"] == exclude:
                continue
            out.append((prefix + d["name"], d["id"]))
            out += self.group_options(exclude, d["children"], prefix + d["name"] + " / ")
        return out

    def project_page(self, node):
        d = node.data
        if repo_slug(d["url"]) and d["id"] not in self.fetching and self.readme_text(d) is None:
            self.fetch_readme(d, lambda: self._refresh_if_current(d))
        page = Adw.PreferencesPage()

        # what is this?
        about = Adw.PreferencesGroup()
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, css_classes=["card"])
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, margin_top=14,
                        margin_bottom=14, margin_start=16, margin_end=16)
        card.append(inner)
        title = Gtk.Label(xalign=0, wrap=True, css_classes=["title-2"])
        node.bind_property("title", title, "label", GObject.BindingFlags.SYNC_CREATE)
        inner.append(title)
        meta = [d.get("language"), "Private" if d.get("private") else "Public" if d["url"] else None,
                f"Updated {d['updated']}" if d.get("updated") else None,
                "Live site" if d.get("site") else None]
        meta = " · ".join(m for m in meta if m)
        if meta:
            inner.append(Gtk.Label(label=meta, xalign=0, css_classes=["dim-label", "caption"]))
        text = self.readme_text(d)
        summary, bullets = summarize(text) if text else ("", [])
        if summary:
            blurb = summary
        elif d["id"] in self.fetching:
            blurb = "Reading the README…"
        elif d["description"]:
            blurb = d["description"]
        elif text == "":
            blurb = "This repo has no README yet, so there's nothing to explain."
        else:
            blurb = "No README to read yet. Add a repository URL or a folder and Grove will summarise it."
        inner.append(Gtk.Label(label=blurb, xalign=0, wrap=True, selectable=True))
        if bullets:
            inner.append(Gtk.Label(label="\n".join("•  " + b for b in bullets), xalign=0,
                                   wrap=True, selectable=True))
        if text:
            row = Gtk.Box(spacing=8, margin_top=4)
            read = Gtk.Button(label=self.T("Read full README"))
            read.connect("clicked", lambda *_: self.show_readme(d))
            row.append(read)
            if d["url"]:
                again = Gtk.Button(icon_name="view-refresh-symbolic", css_classes=["flat"],
                                   tooltip_text="Download the README again")
                again.connect("clicked", lambda *_: self.refetch(d))
                row.append(again)
            inner.append(row)
        about.add(card)
        page.add(about)

        # launch
        launch = Adw.PreferencesGroup()
        bar = Gtk.Box(spacing=8, homogeneous=True)
        for icon, label, tip, fn, css in [
            ("document-edit-symbolic", "Editor", "Open the project folder in your editor",
             lambda *_: self.open_editor(d), []),
            ("utilities-terminal-symbolic", "Terminal", "Open a terminal in the project folder",
             lambda *_: self.open_terminal(d), []),
            ("system-software-install-symbolic", "Install", "Download it first if needed, then install it",
             lambda b: self.install(d, b), []),
            ("media-playback-start-symbolic", "Run", "Run it (opens the live site for deployed web projects; otherwise runs in a terminal)",
             lambda b: self.run_project(d, b), ["suggested-action"]),
            ("folder-open-symbolic", "Files", "Open the folder in your file manager",
             lambda *_: self.open_folder(d), []),
            ("web-browser-symbolic", "GitHub", "Open the repository page in your browser",
             lambda *_: self.open_url(d), []),
        ] + ([("applications-internet-symbolic", "Live", "Open the deployed site (GitHub Pages)",
               lambda *_: self.open_site(d), [])] if d.get("site") else []):
            b = Gtk.Button(child=Adw.ButtonContent(icon_name=icon, label=self.T(label)),
                           css_classes=css, tooltip_text=tip)
            b.connect("clicked", fn)
            bar.append(b)
        launch.add(bar)
        newer = self.latest_tags.get(d["id"])
        if newer and d.get("release") and newer["tag"] != d["release"]["tag"]:
            up = Gtk.Button(child=Adw.ButtonContent(icon_name="software-update-available-symbolic",
                                                    label=f"Update to {newer['tag']} (you have {d['release']['tag']})"),
                            css_classes=["suggested-action"], margin_top=8)
            up.connect("clicked", lambda b: self.update_release(d, b))
            launch.add(up)
        elif d.get("release") and self.cloned(d):
            GLib.idle_add(self.check_update, d)
        page.add(launch)

        # advanced, tucked away
        adv = Adw.PreferencesGroup()
        exp = Adw.ExpanderRow(title=self.T("Edit details and commands"),
                              subtitle="Name, group, folder, install and run commands")
        exp.add_row(self.entry("Name", d, "name", node))
        exp.add_row(self.entry("Repository URL", d, "url"))
        exp.add_row(self.entry("Description", d, "description"))
        exp.add_row(self.parent_combo(d))
        path_row = self.entry("Folder", d, "path")
        pick = Gtk.Button(icon_name="folder-open-symbolic", valign=Gtk.Align.CENTER,
                          css_classes=["flat"], tooltip_text="Choose folder")
        pick.connect("clicked", lambda *_: self.pick_folder(d, path_row))
        path_row.add_suffix(pick)
        exp.add_row(path_row)
        install_row = self.entry("Install command (runs in a terminal)", d, "install")
        run_row = self.entry("Run command (runs in a terminal)", d, "run")
        detect_btn = Gtk.Button(icon_name="system-search-symbolic", valign=Gtk.Align.CENTER,
                                css_classes=["flat"], tooltip_text="Detect install and run commands")
        detect_btn.connect("clicked", lambda *_: self.detect_into(d, install_row, run_row, force=True))
        install_row.add_suffix(detect_btn)
        exp.add_row(install_row)
        exp.add_row(run_row)
        adv.add(exp)
        page.add(adv)

        gone = Adw.PreferencesGroup()
        rm = Gtk.Button(label=self.T("Remove this repo…"), css_classes=["destructive-action"],
                        halign=Gtk.Align.START, tooltip_text="Take it off your list (Delete key)")
        rm.connect("clicked", lambda *_: self.confirm_remove(d))
        gone.add(rm)
        page.add(gone)
        return page

    # ---- readmes -------------------------------------------------------
    def readme_text(self, d):
        """README markdown for a project; "" if it has none, None if not known yet."""
        path = os.path.expanduser(d["path"]) if d["path"] else ""
        if path and os.path.isdir(path):
            for name in sorted(os.listdir(path)):
                if name.lower().startswith("readme"):
                    try:
                        with open(os.path.join(path, name), errors="replace") as f:
                            return f.read()
                    except OSError:
                        pass
        if d["id"] not in self.readmes:
            try:
                with open(os.path.join(CACHE_DIR, d["id"] + ".md")) as f:
                    self.readmes[d["id"]] = f.read()
            except OSError:
                return None
        return self.readmes[d["id"]]

    def blurb(self, d):
        """One-line description for the sidebar."""
        if d.get("description"):
            return d["description"]
        text = self.readme_text(d)
        summary = summarize(text)[0] if text else ""
        return summary[:90] + ("…" if len(summary) > 90 else "")

    def search_store(self):
        store = Gio.ListStore(item_type=Node)
        for d, *_ in sorted(walk(self.tree), key=lambda t: t[0]["name"].lower()):
            if d["type"] != "project":
                continue
            text = self.readme_text(d)
            hay = " ".join([d["name"], d.get("description", ""), d.get("language", ""),
                            summarize(text)[0] if text else ""]).lower()
            if self.query in hay:
                store.append(Node(d, None, self.blurb(d)))
        return store

    def refresh_subtitles(self):
        if not self.sel:
            return
        model = self.sel.get_model()
        for i in range(model.get_n_items()):
            node = model.get_item(i).get_item()
            if not node.is_group:
                node.props.subtitle = self.blurb(node.data)

    def _refresh_if_current(self, d):
        cur = self.current()
        if cur and cur.data["id"] == d["id"]:
            self.show_detail()
        self.refresh_subtitles()

    def fetch_readme(self, d, then=None):
        slug = repo_slug(d["url"])
        if not slug:
            if then:
                then()
            return
        if d["id"] in self.fetching:  # already downloading: just wait for it
            if then:
                self.fetching[d["id"]].append(then)
            return
        self.fetching[d["id"]] = [then] if then else []

        def finish(text):
            callbacks = self.fetching.pop(d["id"], [])
            if text is not None:
                os.makedirs(CACHE_DIR, exist_ok=True)
                with open(os.path.join(CACHE_DIR, d["id"] + ".md"), "w") as f:
                    f.write(text)
                self.readmes[d["id"]] = text
            for cb in callbacks:
                cb()

        def public_api():
            # no gh, or gh can't see it: ask the public API (private repos just 404 here)
            def done(proc, out, err):
                if proc.get_exit_status() == 0:
                    finish(out)
                else:  # a public repo that 404s has no README; a private one is unknown
                    finish("" if not d.get("private") and "404" in (err or "") else None)
            self.run_async(["curl", "-fsSL", "-H", "Accept: application/vnd.github.raw+json",
                            f"https://api.github.com/repos/{slug}/readme"], done)

        if not shutil.which("gh"):
            public_api()
            return

        def done(proc, out, err):
            if proc.get_exit_status() == 0:
                finish(base64.b64decode(out).decode("utf-8", "replace"))
            elif "404" in (err or ""):  # signed in and still 404: the repo has no README
                finish("")
            else:
                public_api()
        self.run_async(["gh", "api", f"repos/{slug}/readme", "--jq", ".content"], done)

    def refetch(self, d):
        self.readmes.pop(d["id"], None)
        try:
            os.remove(os.path.join(CACHE_DIR, d["id"] + ".md"))
        except OSError:
            pass
        self.fetch_readme(d, lambda: self._refresh_if_current(d))
        self.show_detail()

    def prefetch_readmes(self, force=False):
        """Download READMEs for every project in the background, one at a time."""
        todo = [d for d, *_ in walk(self.tree) if d["type"] == "project" and d["url"]
                and (force or self.readme_text(d) is None)]
        if force:
            for d in todo:
                self.readmes.pop(d["id"], None)

        def nxt():
            self.refresh_subtitles()
            if todo:
                d = todo.pop(0)
                self.fetch_readme(d, lambda: (self._refresh_if_current(d), nxt()))
            elif force:
                self.toast("READMEs refreshed")
                self.show_detail()
        if todo:
            nxt()

    def check_site(self, d, then=None):
        """Note whether the repo has a live GitHub Pages site (no login needed)."""
        url = pages_url(d["url"])
        if not url or d.get("private"):
            d["site"], d["site_checked"] = "", time.time()
            if then:
                then()
            return

        def done(proc, out, err):
            d["site"] = url if (out or "").strip() == "200" else ""
            d["site_checked"] = time.time()
            self.save()
            self._refresh_if_current(d)
            if then:
                then()
        self.run_async(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "-L", "--max-time", "8", url], done)

    def check_all_sites(self):
        todo = [d for d, *_ in walk(self.tree) if d["type"] == "project" and d["url"]
                and time.time() - d.get("site_checked", 0) > 86400]

        def nxt():
            if todo:
                self.check_site(todo.pop(0), nxt)
        nxt()

    def show_readme(self, d):
        buf = Gtk.TextBuffer()
        render_markdown(buf, self.readme_text(d) or "")
        view = Gtk.TextView(buffer=buf, editable=False, cursor_visible=False,
                            wrap_mode=Gtk.WrapMode.WORD_CHAR, left_margin=18, right_margin=18,
                            top_margin=12, bottom_margin=18)
        tv = Adw.ToolbarView(content=Gtk.ScrolledWindow(child=view), css_classes=["readme"])
        tv.add_top_bar(Adw.HeaderBar())
        dlg = Adw.Dialog(title=f"{d['name']}: README", content_width=720, content_height=640)
        dlg.set_child(tv)
        dlg.present(self)

    def group_page(self, node):
        d = node.data
        page = Adw.PreferencesPage()
        g = Adw.PreferencesGroup(title=self.T("Group"))
        g.add(self.entry("Name", d, "name", node))
        g.add(self.parent_combo(d))
        page.add(g)
        acts = Adw.PreferencesGroup()
        box = Gtk.Box(spacing=8)
        add_p = Gtk.Button(label="Add project here")
        add_p.connect("clicked", lambda *_: self.add_project())
        add_g = Gtk.Button(label="Add subgroup")
        add_g.connect("clicked", lambda *_: self.add_group())
        rm = Gtk.Button(label="Delete group…", css_classes=["destructive-action"])
        rm.connect("clicked", lambda *_: self.confirm_remove(d))
        for b in (add_p, add_g) if d.get("pinned") else (add_p, add_g, rm):
            box.append(b)
        acts.add(box)
        acts.set_description("Pinned: this account's public repos always show first and re-sync automatically."
                             if d.get("pinned") else "Deleting a group moves its contents up one level.")
        page.add(acts)
        return page

    # ---- tree edits --------------------------------------------------
    def selected_group(self):
        node = self.current()
        if node is None:
            return None
        if node.is_group:
            return node.data
        return self.find(node.data["id"])[2]

    def add_group(self):
        grp = self.selected_group()
        g = new_group("New group")
        (grp["children"] if grp else self.tree).append(g)
        self.rebuild(g["id"])

    def add_project(self):
        grp = self.selected_group()
        p = new_project("New project")
        (grp["children"] if grp else self.tree).append(p)
        self.rebuild(p["id"])

    def remove_selected(self):
        node = self.current()
        if node is None:
            self.toast("Select a repo or group first")
        else:
            self.confirm_remove(node.data)

    def local_copy(self, d):
        """(path, has_changes) for a clone Grove may offer to delete, else None.

        Only a git checkout whose origin is this very repo qualifies, so a stray folder
        (or anything like ~/Downloads) is never offered."""
        path = os.path.realpath(os.path.expanduser(d["path"])) if d.get("path") else ""
        home = os.path.realpath(os.path.expanduser("~"))
        slug = repo_slug(d.get("url"))
        if not (path and slug and os.path.isdir(os.path.join(path, ".git"))):
            return None
        if path == home or home.startswith(path + os.sep):
            return None

        def git(*args):
            return subprocess.run(["git", "-C", path, *args], capture_output=True, text=True,
                                  timeout=10).stdout.strip()
        try:
            remote, dirty = git("remote", "get-url", "origin"), bool(git("status", "--porcelain"))
        except (OSError, subprocess.SubprocessError):
            return None
        return (path, dirty) if slug.lower() in remote.lower() else None

    def confirm_remove(self, d):
        if d["type"] == "group":
            body = "The group goes away; the repos inside move up one level."
            local = None
        else:
            body = "This takes it off your Grove list. The GitHub repo and your files stay untouched."
            local = self.local_copy(d)
        dlg = Adw.AlertDialog(heading=f"Remove {d['name']}?", body=body)
        dlg.add_response("cancel", "Cancel")
        dlg.add_response("remove", "Remove from list")
        dlg.set_response_appearance("remove", Adw.ResponseAppearance.DESTRUCTIVE)
        if local:
            path, dirty = local
            dlg.set_body(body + f"\n\nThere is a copy on this computer:\n{path}"
                         + ("\nIt has uncommitted changes that would be lost." if dirty else ""))
            dlg.add_response("delete", "Remove and delete local copy")
            dlg.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
        dlg.set_default_response("cancel")
        dlg.set_close_response("cancel")
        dlg.connect("response", lambda _d, r: r != "cancel" and self.remove(d, delete_local=(r == "delete")))
        dlg.present(self)

    def remove(self, d, delete_local=False):
        note = ""
        if d["type"] == "project":
            local = self.local_copy(d) if delete_local else None
            if local:  # re-checked here, right before deleting
                shutil.rmtree(local[0], ignore_errors=True)
                note = " and deleted its local copy"
            if d.get("url"):  # keep it gone: otherwise the next sync would add it straight back
                self.data.setdefault("hidden", [])
                if d["url"] not in self.data["hidden"]:
                    self.data["hidden"].append(d["url"])
        _, sibs, parent = self.find(d["id"])
        sibs.remove(d)
        if d["type"] == "group":
            sibs.extend(d["children"])
        self.expanded.discard(d["id"])
        self.sel.set_selected(Gtk.INVALID_LIST_POSITION)
        self.rebuild(parent["id"] if parent else None)
        if not parent:
            self.sel.set_selected(Gtk.INVALID_LIST_POSITION)
        self.toast(f"Removed {d['name']}{note}")

    def restore_removed(self):
        n = len(self.data.get("hidden", []))
        self.data["hidden"] = []
        self.save()
        self.toast(f"Brought back {n} removed repo{'s' if n != 1 else ''}" if n else "Nothing was removed")
        if n:
            self.sync()

    # ---- launching ---------------------------------------------------
    def project_dir(self, d):
        path = os.path.expanduser(d["path"]) if d["path"] else ""
        if not os.path.isdir(path):
            self.toast("Folder not found: clone the project or set its folder first")
            return None
        return path

    def report(self, err):
        if err:
            self.toast(err)

    def open_editor(self, d):
        path = self.project_dir(d)
        if not path:
            return
        argv = shlex.split(self.settings["editor"])
        argv = [a.replace("{path}", path) for a in argv] if any("{path}" in a for a in argv) else argv + [path]
        self.report(spawn(argv, path))

    def detect_into(self, d, install_row, run_row, force=False):
        path = self.project_dir(d)
        if not path:
            return
        install, run = detect_commands(path)
        if not (install or run):
            self.toast("Couldn't recognise this project type, set the commands by hand")
            return
        for key, row, val in (("install", install_row, install), ("run", run_row, run)):
            if val and (force or not d.get(key)):
                row.set_text(val)  # fires "changed", which saves
        self.toast("Filled in detected commands")

    def fill_missing(self, d):
        """Detect commands for any that are empty; returns True if anything was filled."""
        path = os.path.expanduser(d["path"]) if d["path"] else ""
        if not os.path.isdir(path):
            return
        install, run = detect_commands(path)
        d["install"] = d.get("install") or install
        d["run"] = d.get("run") or run
        self.save()

    def install(self, d, button=None):
        if not self.cloned(d):
            if not d["url"]:
                self.toast("Set a repository URL or folder first")
                return
            self.clone(d, button, then=lambda: self.install(d))
            return
        self.fill_missing(d)
        if not d.get("install"):
            run = (d.get("run") or "").strip()
            if d.get("release", {}).get("kind") == "download" and run.startswith("./"):
                try:   # a downloaded program with no installer: put it in the app menu
                    menu_entry(os.path.expanduser(d["path"]), d["name"], run)
                    self.toast(f"Added {d['name']} to your app menu")
                except OSError as e:
                    self.toast(f"Couldn't add it to the app menu: {e}")
                return
            self.toast("No install step detected: it's ready to run, or set one by hand")
            return
        self.open_terminal(d, d["install"])

    def open_site(self, d):
        if d.get("site"):
            self.report(spawn(["xdg-open", d["site"]]))

    def run_project(self, d, button=None):
        if d.get("site") and not d.get("run"):  # a deployed web project: "run" means open it
            if self.cloned(d):
                self.fill_missing(d)
            if not d.get("run"):
                self.open_site(d)
                return
        if not self.cloned(d):
            if not d["url"]:
                self.toast("Set a repository URL or folder first")
                return
            self.clone(d, button, then=lambda: self._launch(d, with_install=True))
            return
        self._launch(d, with_install=False)

    def _launch(self, d, with_install):
        self.fill_missing(d)
        steps = [c for c in ((d.get("install") if with_install else ""), d.get("run")) if c]
        if not d.get("run"):
            index = os.path.join(os.path.expanduser(d["path"]), "index.html")
            if os.path.exists(index):  # plain static page: open it in the browser
                self.report(spawn(["xdg-open", index]))
                if not steps:
                    return
            else:
                self.toast("No run command: set one (or press detect)")
        if steps:
            self.open_terminal(d, " && ".join(steps))

    def cloned(self, d):
        return bool(d["path"]) and os.path.isdir(os.path.expanduser(d["path"]))

    def open_terminal(self, d, cmd=None):
        path = self.project_dir(d)
        if not path:
            return
        term = shlex.split(self.settings["terminal"])
        flags = TERMINAL_FLAGS.get(os.path.basename(term[0]), ["-e"])
        # show what is being run and how it ended, so a silent failure isn't a mystery
        shell = (f'printf "%s\\n" {shlex.quote("$ " + cmd)}; {cmd}; rc=$?; echo; '
                 f'echo "[Grove: finished with exit code $rc]"; exec "${{SHELL:-sh}}"') if cmd else 'exec "${SHELL:-sh}"'
        argv = term + [f.replace("{path}", path) for f in flags] + ["sh", "-c", shell]
        self.report(spawn(argv, path))

    def open_folder(self, d):
        path = self.project_dir(d)
        if path:
            self.report(spawn(["xdg-open", path]))

    def open_url(self, d):
        if d["url"]:
            self.report(spawn(["xdg-open", d["url"]]))
        else:
            self.toast("No repository URL set")

    def pick_folder(self, d, row):
        dlg = Gtk.FileDialog(title="Project folder")

        def done(dlg, res):
            try:
                f = dlg.select_folder_finish(res)
            except GLib.Error:
                return
            row.set_text(f.get_path())  # fires "changed", which saves
        dlg.select_folder(self, None, done)

    # ---- github ------------------------------------------------------
    def run_async(self, argv, cb):
        try:
            proc = Gio.Subprocess.new(argv, Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_PIPE)
        except GLib.Error as e:
            self.toast(f"Could not run {argv[0]}: {e.message}")
            return
        proc.communicate_utf8_async(None, None, lambda p, r: cb(p, *p.communicate_utf8_finish(r)[1:]))

    REPO_FIELDS = "name,url,description,isPrivate,isArchived,primaryLanguage,updatedAt"

    def accounts(self):
        """Featured account first, then any others the user follows."""
        extra = [u for u in self.settings.get("extra_users", []) if u.lower() != FEATURED.lower()]
        return [FEATURED] + extra

    def sync(self):
        self._added, self._quiet = 0, False
        self.toast("Fetching repos from GitHub…")
        self.sync_accounts(self.sync_mine)

    def auto_sync(self):
        """Keep the featured account's group present and fresh without any login."""
        has = any(d["type"] == "group" and d["name"].lower() == FEATURED.lower() for d in self.tree)
        if not has or time.time() - self.data.get("last_sync", 0) > 12 * 3600:
            self._added, self._quiet = 0, True
            self.sync_accounts()

    def sync_accounts(self, then=None):
        users = self.accounts()

        def nxt():
            if users:
                self.sync_public_api(users.pop(0), nxt)
            elif then:
                then()
            else:
                self.finish_sync()
        nxt()

    def sync_mine(self):
        """The signed-in gh account's own repos (private ones too, unless public-only)."""
        if not shutil.which("gh"):
            self.finish_sync()
            return
        argv = ["gh", "repo", "list", "--limit", "500", "--json", self.REPO_FIELDS]
        if self.settings.get("public_only"):
            argv += ["--visibility", "public"]

        def done(proc, out, err):
            if proc.get_exit_status() == 0:
                self._added += self._import(json.loads(out), INBOX)
            self.finish_sync()
        self.run_async(argv, done)

    def sync_public_api(self, user, then):
        """List a user's public repos through GitHub's REST API, with no login."""
        repos = []

        def page(n):
            url = f"https://api.github.com/users/{user}/repos?per_page=100&type=owner&sort=updated&page={n}"
            self.run_async(["curl", "-fsSL", "-H", "Accept: application/vnd.github+json", url],
                           lambda proc, out, err: got(n, proc, out))

        def got(n, proc, out):
            if proc.get_exit_status() != 0:
                if not self._quiet:
                    self.toast(f"Couldn't read public repos for '{user}' (check the name, or the rate limit)")
                then()
                return
            batch = json.loads(out)
            repos.extend({"name": r["name"], "url": r["html_url"], "description": r["description"],
                          "isPrivate": False, "isArchived": r["archived"],
                          "primaryLanguage": {"name": r["language"]} if r["language"] else None,
                          "updatedAt": r["pushed_at"] or r["updated_at"]}
                         for r in batch if not r["private"])
            if len(batch) == 100 and n < 5:
                page(n + 1)
            else:
                self._added += self._import(repos, user, pinned=user.lower() == FEATURED.lower())
                then()
        page(1)

    def finish_sync(self):
        self.data["last_sync"] = time.time()
        self.rebuild()
        self.prefetch_readmes()
        self.check_all_sites()
        n = self._added
        if not self._quiet:
            self.toast(f"Added {n} new repo{'s' if n != 1 else ''}" if n else "Already up to date")

    def _import(self, repos, group_name=INBOX, pinned=False):
        """Add new repos under a top-level group; returns how many were added."""
        if self.settings.get("public_only"):
            repos = [r for r in repos if not r["isPrivate"]]
        known = {d["url"]: d for d, *_ in walk(self.tree) if d["type"] == "project"}
        hidden = set(self.data.get("hidden", []))
        grp = next((d for d in self.tree
                    if d["type"] == "group" and d["name"].lower() == group_name.lower()), None)
        if grp and pinned:
            grp["pinned"] = True
        added = 0
        for r in repos:
            lang = (r.get("primaryLanguage") or {}).get("name", "")
            updated = (r.get("updatedAt") or "")[:10]
            if r["url"] in known:
                known[r["url"]].update(description=r["description"] or "", private=r["isPrivate"],
                                       language=lang, updated=updated)
                continue
            if r["isArchived"] or r["url"] in hidden:
                continue
            if grp is None:
                grp = new_group(group_name)
                if pinned:
                    grp["pinned"] = True
                self.tree.append(grp)
            guess = os.path.join(self.settings["projects_dir"], r["name"])
            grp["children"].append(new_project(
                r["name"], url=r["url"], description=r["description"] or "",
                private=r["isPrivate"], path=guess if os.path.isdir(guess) else "",
                language=lang, updated=updated))
            added += 1
        return added

    def _busy(self, button, label, toast_text):
        if button:
            button.set_sensitive(False)
            child = button.get_child()
            (child.set_label if isinstance(child, Adw.ButtonContent) else button.set_label)(label)
        else:
            self.toast(toast_text)

    def clone(self, d, button, then=None):
        """Get a project onto this computer: its latest release when it has one (a ready-to-run download, or
        the release's source at its tag), otherwise a plain git clone. Run then() when it is there."""
        if not d["path"]:
            d["path"] = os.path.join(self.settings["projects_dir"], d["name"])
        slug = repo_slug(d["url"])
        if slug and self.settings.get("prefer_releases", True):
            self._busy(button, "Looking for a release…", f"Looking for a release of {d['name']}…")
            self.latest_release(slug, lambda rel: self._acquire(d, button, rel, then))
        else:
            self._git_clone(d, button, None, then)

    def latest_release(self, slug, cb):
        """cb(release or None): the repo's latest release as {tag, assets}, using gh if there is one."""
        if shutil.which("gh"):
            argv = ["gh", "release", "view", "--repo", slug, "--json", "tagName,assets"]
        else:
            argv = ["curl", "-fsSL", "-H", "Accept: application/vnd.github+json",
                    f"https://api.github.com/repos/{slug}/releases/latest"]
        self.run_async(argv, lambda proc, out, _e: cb(parse_release(out) if proc.get_exit_status() == 0 else None))

    def _acquire(self, d, button, rel, then):
        if not rel:
            self._git_clone(d, button, None, then)
            return
        asset = pick_asset(rel["assets"])
        if not asset:   # a release with no program to download: its source, at the release's tag
            self._git_clone(d, button, rel["tag"], then)
            return
        self._busy(button, f"Downloading {rel['tag']}…", f"Downloading {d['name']} {rel['tag']}…")
        self._download_release(d, rel, asset, lambda ok: self._acquired(d, button, ok, then))

    def _download_release(self, d, rel, asset, cb):
        """Download the asset and unpack it into the project's folder. cb(True/False)."""
        slug = repo_slug(d["url"])
        tmp = tempfile.mkdtemp(prefix="grove-")
        out = os.path.join(tmp, asset["name"])
        if shutil.which("gh"):
            argv = ["gh", "release", "download", rel["tag"], "--repo", slug, "--pattern", asset["name"],
                    "--dir", tmp, "--clobber"]
        else:
            argv = ["curl", "-fL", "-o", out, asset["url"]]

        def done(proc, _o, err):
            ok = proc.get_exit_status() == 0 and os.path.exists(out)
            try:
                if ok:
                    path = os.path.expanduser(d["path"])
                    if os.path.isdir(path) and os.listdir(path):   # an update: keep the old one beside it
                        shutil.move(path, f"{path}.old-{int(time.time())}")
                    unpack(out, path)
                    d["release"] = {"tag": rel["tag"], "kind": "download", "asset": asset["name"]}
                    d["run"] = d["install"] = ""   # work out how to run this one afresh
                else:
                    lines = (err or "").strip().splitlines()
                    self.toast(lines[-1] if lines else "Download failed")
            except (OSError, shutil.Error) as e:
                ok = False
                self.toast(f"Couldn't unpack it: {e}")
            shutil.rmtree(tmp, ignore_errors=True)
            cb(ok)
        self.run_async(argv, done)

    def _acquired(self, d, button, ok, then):
        if ok:
            self.toast(f"Downloaded {d['name']} {d['release']['tag']}")
            self.fill_missing(d)
        self.rebuild(d["id"])
        if ok and then:
            then()

    def _git_clone(self, d, button, tag, then):
        path = os.path.expanduser(d["path"])
        self._busy(button, "Cloning…", f"Cloning {d['name']}…")
        if shutil.which("gh"):
            argv = ["gh", "repo", "clone", d["url"], path] + (["--", "--branch", tag] if tag else [])
        else:
            argv = ["git", "clone"] + (["--branch", tag] if tag else []) + [d["url"], path]

        def done(proc, _out, err):
            if proc.get_exit_status() == 0:
                if tag:
                    d["release"] = {"tag": tag, "kind": "source"}
                self.toast(f"Cloned {d['name']}" + (f" at {tag}" if tag else ""))
                self.fill_missing(d)
            else:
                lines = (err or "").strip().splitlines()
                self.toast(lines[-1] if lines else "Clone failed")
            self.rebuild(d["id"])
            if then and proc.get_exit_status() == 0:
                then()
        self.run_async(argv, done)

    # ---- updates ---------------------------------------------------------
    def check_update(self, d):
        """Once per session per project: is there a newer release than the one on disk?"""
        slug = repo_slug(d["url"])
        if not (slug and d.get("release")) or d["id"] in self.update_checked:
            return
        self.update_checked.add(d["id"])

        def got(rel):
            if rel and rel["tag"] != d["release"]["tag"]:
                self.latest_tags[d["id"]] = rel
                self._refresh_if_current(d)
        self.latest_release(slug, got)

    def update_release(self, d, button=None):
        rel = self.latest_tags.get(d["id"])
        if not rel:
            return
        path = os.path.expanduser(d["path"])
        self._busy(button, "Updating…", f"Updating {d['name']}…")
        if d["release"].get("kind") == "download":
            asset = pick_asset(rel["assets"])
            if not asset:
                self.toast("The new release has no download for this PC")
                return
            self._download_release(d, rel, asset, lambda ok: self._updated(d, rel, ok))
            return

        def checked_out(proc, _o, err):
            if proc.get_exit_status() == 0:
                d["release"]["tag"] = rel["tag"]
                self.latest_tags.pop(d["id"], None)
                self.toast(f"Updated {d['name']} to {rel['tag']}")
            else:
                lines = (err or "").strip().splitlines()
                self.toast(lines[-1] if lines else "Update failed (uncommitted changes?)")
            self.save()
            self.rebuild(d["id"])
        self.run_async(["git", "-C", path, "fetch", "--tags", "--force", "--quiet"],
                       lambda p, _o, _e: self.run_async(["git", "-C", path, "checkout", "-q", rel["tag"]], checked_out))

    def _updated(self, d, rel, ok):
        if ok:
            self.latest_tags.pop(d["id"], None)
            self.toast(f"Updated {d['name']} to {rel['tag']} (the old copy is kept beside it)")
            self.fill_missing(d)
        self.rebuild(d["id"])

    # ---- settings ----------------------------------------------------
    def show_settings(self):
        s = self.settings
        lst = Gtk.ListBox(css_classes=["boxed-list"], selection_mode=Gtk.SelectionMode.NONE)
        rows = {}
        for key, title in [("editor", "Editor command  ({path} optional)"),
                           ("terminal", "Terminal"),
                           ("projects_dir", "Projects folder")]:
            rows[key] = Adw.EntryRow(title=title, text=s[key])
            lst.append(rows[key])
        user_row = Adw.EntryRow(title="Follow other GitHub users (comma separated)",
                                text=", ".join(s.get("extra_users", [])))
        pub_row = Adw.SwitchRow(title="Public repos only", active=s.get("public_only", False),
                                subtitle="Never import private repositories")
        rel_row = Adw.SwitchRow(title="Download releases", active=s.get("prefer_releases", True),
                                subtitle="Install and Run get a repo's latest release when it has one, otherwise clone it")
        lst.append(user_row)
        lst.append(pub_row)
        lst.append(rel_row)
        dlg = Adw.AlertDialog(heading="Settings", extra_child=lst,
                              body=f"{FEATURED}'s public repos are always shown first. "
                                   "Add other GitHub users to follow their public repos too.")
        dlg.add_response("cancel", "Cancel")
        dlg.add_response("save", "Save")
        dlg.set_response_appearance("save", Adw.ResponseAppearance.SUGGESTED)

        def resp(_d, r):
            if r == "save":
                for k, row in rows.items():
                    if row.get_text().strip():
                        s[k] = row.get_text().strip()
                names = [n.strip().lstrip("@") for n in re.split(r"[,\s]+", user_row.get_text())]
                s["extra_users"] = list(dict.fromkeys(n for n in names if USERNAME.fullmatch(n)))
                s["public_only"] = pub_row.get_active()
                s["prefer_releases"] = rel_row.get_active()
                self.save()
                self.sync()
        dlg.connect("response", resp)
        dlg.present(self)


class App(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID)

    def do_activate(self):
        Gtk.Window.set_default_icon_name(ICON_NAME)
        (self.props.active_window or Grove(self)).present()


if __name__ == "__main__":
    sys.exit(App().run(sys.argv))
