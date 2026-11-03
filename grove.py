#!/usr/bin/env python3
"""Grove: organise your GitHub projects in a custom tree and launch them."""
import base64
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import uuid

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, GLib, GObject, Gtk  # noqa: E402

APP_ID = "io.github.grove.Launcher"
CONFIG = os.path.join(GLib.get_user_config_dir(), "grove", "config.json")
CACHE_DIR = os.path.join(GLib.get_user_cache_dir(), "grove", "readmes")
INBOX = "Unsorted"

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
        "github_user": "",     # sync this account's public repos (works without gh)
        "public_only": False,  # never import private repos
    }


def new_id():
    return uuid.uuid4().hex[:12]


def new_group(name):
    return {"type": "group", "id": new_id(), "name": name, "children": []}


def new_project(name, **kw):
    return {"type": "project", "id": new_id(), "name": name, "url": "",
            "description": "", "path": "", "install": "", "run": "", "private": False, **kw}


def walk(items, parent=None):
    """Yield (node, siblings, parent_group) for every node under items."""
    for d in list(items):
        yield d, items, parent
        if d["type"] == "group":
            yield from walk(d["children"], d)


def detect_commands(path):
    """Guess (install, run) shell commands from the files in a project."""
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
    for d in sorted(items, key=lambda d: (d["type"] != "group", d["name"].lower())):
        if d["type"] == "group":
            store.append(Node(d, build_store(d["children"], blurb)))
        else:
            store.append(Node(d, None, blurb(d)))
    return store


class Grove(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="Grove", default_width=1000, default_height=680)
        self.load()
        self.sel = None
        self.expanded = set(self.data.get("expanded", []))
        self.query = ""
        self.readmes = {}        # project id -> README text ("" = repo has none)
        self.fetching = set()    # project ids with a README download in flight

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
        menu.append("Hackers theme", "win.hackers")
        menu.append("Settings", "win.settings")
        header.pack_end(Gtk.MenuButton(icon_name="open-menu-symbolic", menu_model=menu))
        act = Gio.SimpleAction.new("settings", None)
        act.connect("activate", lambda *_: self.show_settings())
        self.add_action(act)
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
        GLib.idle_add(self.prefetch_readmes)

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
                box.append(Gtk.Label(label=BANNER, css_classes=["banner"], selectable=False))
                box.append(Gtk.Label(label="H A C K   T H E   P L A N E T", css_classes=["tagline"]))
                page.set_child(box)
                parent = box
            else:
                page.set_icon_name("folder-symbolic")
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
        if self.readme_text(d) is None and d["url"]:
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
                f"Updated {d['updated']}" if d.get("updated") else None]
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
            ("system-software-install-symbolic", "Install", "Download it if needed, then run the install command",
             lambda *_: self.install(d), []),
            ("media-playback-start-symbolic", "Run", "Run the project in a terminal",
             lambda *_: self.run_project(d), ["suggested-action"]),
            ("folder-open-symbolic", "Files", "Open the folder in your file manager",
             lambda *_: self.open_folder(d), []),
            ("web-browser-symbolic", "GitHub", "Open the repository page in your browser",
             lambda *_: self.open_url(d), []),
        ]:
            b = Gtk.Button(child=Adw.ButtonContent(icon_name=icon, label=self.T(label)),
                           css_classes=css, tooltip_text=tip)
            b.connect("clicked", fn)
            bar.append(b)
        launch.add(bar)
        page.add(launch)

        if d["url"] and not self.cloned(d):
            where = d["path"] or os.path.join(self.settings["projects_dir"], d["name"])
            nudge = Adw.PreferencesGroup()
            clone = Adw.ActionRow(title="Not on this computer yet", subtitle=f"Clone downloads it to {where}")
            btn = Gtk.Button(label="Clone", valign=Gtk.Align.CENTER, css_classes=["suggested-action"])
            btn.connect("clicked", lambda b: self.clone(d, b))
            clone.add_suffix(btn)
            nudge.add(clone)
            page.add(nudge)

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
        rm_row = Adw.ActionRow(title="Remove from Grove", subtitle="Only removes this entry; files on disk stay")
        rm = Gtk.Button(label="Remove", valign=Gtk.Align.CENTER, css_classes=["destructive-action"])
        rm.connect("clicked", lambda *_: self.remove(d))
        rm_row.add_suffix(rm)
        exp.add_row(rm_row)
        adv.add(exp)
        page.add(adv)
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
        if not slug or d["id"] in self.fetching:
            if then:
                then()
            return
        self.fetching.add(d["id"])

        def finish(text):
            self.fetching.discard(d["id"])
            if text is not None:
                os.makedirs(CACHE_DIR, exist_ok=True)
                with open(os.path.join(CACHE_DIR, d["id"] + ".md"), "w") as f:
                    f.write(text)
                self.readmes[d["id"]] = text
            if then:
                then()

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
                self.fetch_readme(todo.pop(0), nxt)
            elif force:
                self.toast("READMEs refreshed")
                self.show_detail()
        if todo:
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
        rm = Gtk.Button(label="Delete group", css_classes=["destructive-action"])
        rm.connect("clicked", lambda *_: self.remove(d))
        for b in (add_p, add_g, rm):
            box.append(b)
        acts.add(box)
        acts.set_description("Deleting a group moves its contents up one level.")
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

    def remove(self, d):
        _, sibs, parent = self.find(d["id"])
        sibs.remove(d)
        if d["type"] == "group":
            sibs.extend(d["children"])
        self.expanded.discard(d["id"])
        self.rebuild(parent["id"] if parent else None)
        self.sel.set_selected(Gtk.INVALID_LIST_POSITION) if not parent else None
        self.toast(f"Removed {d['name']}" + ("" if d["type"] == "group" else " (files on disk untouched)"))

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

    def install(self, d):
        if not self.cloned(d):
            if not d["url"]:
                self.toast("Set a repository URL or folder first")
                return
            self.clone(d, None, then=lambda: self.install(d))
            return
        self.fill_missing(d)
        if not d.get("install"):
            self.toast("No install command: set one (or press detect)")
            return
        self.open_terminal(d, d["install"])

    def run_project(self, d):
        if not self.cloned(d):
            self.toast("Not cloned yet: press Install to clone and set it up")
            return
        self.fill_missing(d)
        if not d["run"]:
            self.toast("No run command: set one (or press detect)")
            return
        self.open_terminal(d, d["run"])

    def cloned(self, d):
        return bool(d["path"]) and os.path.isdir(os.path.expanduser(d["path"]))

    def open_terminal(self, d, cmd=None):
        path = self.project_dir(d)
        if not path:
            return
        term = shlex.split(self.settings["terminal"])
        flags = TERMINAL_FLAGS.get(os.path.basename(term[0]), ["-e"])
        shell = f'{cmd}; exec "${{SHELL:-sh}}"' if cmd else 'exec "${SHELL:-sh}"'
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

    def sync(self):
        user = self.settings.get("github_user", "").strip()
        self.toast(f"Fetching {'public ' if self.settings.get('public_only') or user else ''}repos from GitHub…")
        if not shutil.which("gh"):
            if user:
                self.sync_public_api(user)
            else:
                self.toast("Install gh and sign in, or enter a GitHub username in Settings")
            return
        argv = ["gh", "repo", "list"] + ([user] if user else []) + ["--limit", "500", "--json", self.REPO_FIELDS]
        if self.settings.get("public_only"):
            argv += ["--visibility", "public"]

        def done(proc, out, err):
            if proc.get_exit_status() != 0 and user:
                self.sync_public_api(user)  # gh not signed in: the public API still works
            else:
                self._synced(proc, out, err)
        self.run_async(argv, done)

    def sync_public_api(self, user):
        """List a user's public repos through GitHub's REST API, with no login."""
        repos = []

        def page(n):
            url = f"https://api.github.com/users/{user}/repos?per_page=100&type=owner&sort=updated&page={n}"
            self.run_async(["curl", "-fsSL", "-H", "Accept: application/vnd.github+json", url],
                           lambda proc, out, err: got(n, proc, out))

        def got(n, proc, out):
            if proc.get_exit_status() != 0:
                self.toast(f"Couldn't read public repos for '{user}' (check the name, or the rate limit)")
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
                self._import(repos)
        page(1)

    def _synced(self, proc, out, err):
        if proc.get_exit_status() != 0:
            lines = (err or "").strip().splitlines()
            self.toast(lines[-1] if lines else "gh failed (is it installed and logged in?)")
            return
        self._import(json.loads(out))

    def _import(self, repos):
        if self.settings.get("public_only"):
            repos = [r for r in repos if not r["isPrivate"]]
        known = {d["url"]: d for d, *_ in walk(self.tree) if d["type"] == "project"}
        inbox = next((d for d in self.tree if d["type"] == "group" and d["name"] == INBOX), None)
        added = 0
        for r in repos:
            if r["url"] in known:
                known[r["url"]].update(description=r["description"] or "", private=r["isPrivate"],
                                       language=(r.get("primaryLanguage") or {}).get("name", ""),
                                       updated=(r.get("updatedAt") or "")[:10])
                continue
            if r["isArchived"]:
                continue
            if inbox is None:
                inbox = new_group(INBOX)
                self.tree.append(inbox)
            guess = os.path.join(self.settings["projects_dir"], r["name"])
            inbox["children"].append(new_project(
                r["name"], url=r["url"], description=r["description"] or "",
                private=r["isPrivate"], path=guess if os.path.isdir(guess) else "",
                language=(r.get("primaryLanguage") or {}).get("name", ""),
                updated=(r.get("updatedAt") or "")[:10]))
            added += 1
        self.rebuild()
        self.prefetch_readmes()
        self.toast(f"Added {added} new repo{'s' if added != 1 else ''}" if added else "Already up to date")

    def clone(self, d, button, then=None):
        if not d["path"]:
            d["path"] = os.path.join(self.settings["projects_dir"], d["name"])
        path = os.path.expanduser(d["path"])
        if button:
            button.set_sensitive(False)
            button.set_label("Cloning…")
        else:
            self.toast(f"Cloning {d['name']}…")
        tool = ["gh", "repo", "clone"] if shutil.which("gh") else ["git", "clone"]

        def done(proc, _out, err):
            if proc.get_exit_status() == 0:
                self.toast(f"Cloned {d['name']}")
                self.fill_missing(d)
            else:
                lines = (err or "").strip().splitlines()
                self.toast(lines[-1] if lines else "Clone failed")
            self.rebuild(d["id"])
            if then and proc.get_exit_status() == 0:
                then()
        self.run_async(tool + [d["url"], path], done)

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
        user_row = Adw.EntryRow(title="GitHub username to sync (optional, works without gh)",
                                text=s.get("github_user", ""))
        pub_row = Adw.SwitchRow(title="Public repos only", active=s.get("public_only", False),
                                subtitle="Never import private repositories")
        lst.append(user_row)
        lst.append(pub_row)
        dlg = Adw.AlertDialog(heading="Settings", extra_child=lst)
        dlg.add_response("cancel", "Cancel")
        dlg.add_response("save", "Save")
        dlg.set_response_appearance("save", Adw.ResponseAppearance.SUGGESTED)

        def resp(_d, r):
            if r == "save":
                for k, row in rows.items():
                    if row.get_text().strip():
                        s[k] = row.get_text().strip()
                s["github_user"] = user_row.get_text().strip()
                s["public_only"] = pub_row.get_active()
                self.save()
        dlg.connect("response", resp)
        dlg.present(self)


class App(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID)

    def do_activate(self):
        (self.props.active_window or Grove(self)).present()


if __name__ == "__main__":
    sys.exit(App().run(sys.argv))
