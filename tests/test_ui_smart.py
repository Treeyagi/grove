"""Headless UI check for smart groups, drag-move, link drop and the quick launcher (needs a display):
python3 tests/test_ui_smart.py"""
import os
import sys
import tempfile
import time

tmp = tempfile.mkdtemp()
for k in ("XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_CACHE_HOME"):
    os.environ[k] = os.path.join(tmp, k)
    os.makedirs(os.environ[k])
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import grove as g  # noqa: E402
from gi.repository import GLib  # noqa: E402

g.APP_ID = "io.github.grove.UiSmartTest"
failed = []


def check(name, got, want):
    good = got == want
    print(("ok   " if good else "FAIL ") + name + ("" if good else f"\n     got  {got!r}\n     want {want!r}"))
    if not good:
        failed.append(name)


def run(win):
    win.settings["buddy"] = False
    # no network: keep the window's own background jobs quiet
    win.prefetch_readmes = lambda force=False: None
    win.check_all_sites = lambda: None
    inst = os.path.join(tmp, "installed")
    os.makedirs(inst)
    open(os.path.join(inst, "f"), "w").write("x")
    grp = g.new_group("Mine")
    other = g.new_group("Other")
    a = g.new_project("alpha", updated=time.strftime("%Y-%m-%d"), tags=["cli"])
    b = g.new_project("beta", path=inst, url="https://github.com/x/beta")
    grp["children"] += [a, b]
    win.tree[:] = [grp, other]
    win.rebuild()

    items = win.smart_items()
    names = {k["name"]: [p["name"] for p in k["children"]] for k in items[0]["children"]}
    check("smart root present", [i["name"] for i in items], ["Smart groups"])
    check("recently updated", names["Recently updated"], ["alpha"])
    check("never launched", names["Installed, never launched"], ["beta"])
    check("tag group", names["#cli"], ["alpha"])
    model = win.sel.get_model()
    first = model.get_item(0).get_item()
    check("smart group sorts first", first.data["id"], g.SMART_ROOT)
    win.tree.append(g.new_group("zzz"))
    win.tree.pop()
    check("smart groups aren't saved", [d["name"] for d in win.tree], ["Mine", "Other"])

    # drag a repo onto another group
    class Box:
        node = None
        def add_css_class(self, *_): pass
        def remove_css_class(self, *_): pass
    box = Box()
    box.node = g.Node(other)
    check("drop on group", win._drop_on_row(box, a["id"]), True)
    check("moved into Other", [p["name"] for p in other["children"]], ["alpha"])
    check("left Mine", [p["name"] for p in grp["children"]], ["beta"])
    check("dropping where it already is does nothing", win._drop_on_row(box, a["id"]), False)
    box.node = g.Node(b)   # dropped on a repo: joins that repo's group
    check("drop on repo", win._drop_on_row(box, a["id"]), True)
    check("joined repo's group", sorted(p["name"] for p in grp["children"]), ["alpha", "beta"])
    smart = g.Node(items[0]["children"][0])
    box.node = smart
    check("can't drop into smart group", win._drop_on_row(box, a["id"]), False)
    check("unknown id rejected", win._drop_on_row(box, "nope"), False)

    # link drop
    check("non-link toasted and refused", win._drop_link("hello"), False)
    check("repo drag ignored by window", win._drop_link(a["id"]), False)
    win.add_repo("https://github.com/o/newrepo")
    unsorted = next(d for d in win.tree if d["name"] == g.INBOX)
    check("added to Unsorted", [p["url"] for p in unsorted["children"]], ["https://github.com/o/newrepo"])
    check("known link reselects", win._drop_link("https://github.com/o/newrepo"), True)

    # launcher builds and finds things
    win.show_launcher()
    win.show_launcher_ok = True

    # starred import
    win.run_async = lambda argv, cb, slug=None, token=False: cb(
        type("P", (), {"get_exit_status": lambda s: 0})(),
        '[{"name":"cool","html_url":"https://github.com/z/cool","description":"d","private":false,"archived":false,'
        '"language":"Go","pushed_at":"2026-01-01T00:00:00Z","updated_at":"2026-01-01T00:00:00Z"}]', "")
    g.gh_ready = lambda: True
    win.sync_starred()
    wish = next((d for d in win.tree if d["name"] == g.WISHLIST), None)
    check("stars go to Wishlist", wish and [p["name"] for p in wish["children"]], ["cool"])
    win.get_application().quit()
    return False


class T(g.App):
    def do_command_line(self, cl):
        self.activate()
        return 0

    def do_activate(self):
        win = g.Grove(self)
        win.present()
        GLib.timeout_add(300, lambda: run(win))


app = T()
app.run([])
print("\nALL OK" if not failed else f"\n{len(failed)} FAILED")
sys.exit(1 if failed else 0)
