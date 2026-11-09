"""Offline checks for uninstalling (start-menu entries, safe folder deletion): python3 tests/test_uninstall.py"""
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


def desktop(path, name, **kv):
    with open(path, "w") as f:
        f.write("[Desktop Entry]\nType=Application\nName=" + name + "\n" + "".join(f"{k}={v}\n" for k, v in kv.items()))


with tempfile.TemporaryDirectory() as tmp:
    projects = os.path.join(tmp, "Projects")
    proj = os.path.join(projects, "Mission-Control")
    other = os.path.join(projects, "Other")
    apps = os.path.join(tmp, "apps")
    icons = os.path.join(tmp, "icons", "hicolor", "scalable", "apps")
    for d in (proj, other, apps, icons):
        os.makedirs(d)
    desktop(os.path.join(apps, "mission-control.desktop"), "Mission Control",
            Exec=os.path.join(proj, "start-mission-control.sh"), Path=proj, Icon=os.path.join(proj, "mc.svg"))
    desktop(os.path.join(apps, "other.desktop"), "Other", Exec=os.path.join(other, "run.sh"), Icon="other-icon")
    desktop(os.path.join(apps, "firefox.desktop"), "Firefox", Exec="firefox %u", Icon="firefox")
    desktop(os.path.join(apps, "viapath.desktop"), "Via Path", Exec="sh -c run", Path=proj)
    desktop(os.path.join(apps, "named.desktop"), "Named Icon", Exec=os.path.join(proj, "named"), Icon="named-icon")
    open(os.path.join(icons, "named-icon.svg"), "w").write("<svg/>")
    open(os.path.join(icons, "other-icon.svg"), "w").write("<svg/>")

    found = g.start_menu_entries(proj, apps)
    check("finds the entries that point into the project", sorted(n for _f, n, _i in found),
          ["Mission Control", "Named Icon", "Via Path"])
    check("leaves other apps' entries alone", [n for _f, n, _i in g.start_menu_entries(other, apps)], ["Other"])
    check("a project with no entries finds none", g.start_menu_entries(os.path.join(tmp, "nope"), apps), [])
    check("a missing applications folder is fine", g.start_menu_entries(proj, os.path.join(tmp, "missing")), [])

    check("removes the entries it found", g.remove_start_menu(found, os.path.join(tmp, "icons")), 3)
    check("the entry files are gone", sorted(os.listdir(apps)), ["firefox.desktop", "other.desktop"])
    check("an icon installed by name is removed", os.path.exists(os.path.join(icons, "named-icon.svg")), False)
    check("another app's icon stays", os.path.exists(os.path.join(icons, "other-icon.svg")), True)

    check("a folder inside Projects may be deleted", g.safe_project_folder(proj, projects), True)
    check("the Projects folder itself may not", g.safe_project_folder(projects, projects), False)
    check("a folder outside Projects may not", g.safe_project_folder(tmp, projects), False)
    check("home may not", g.safe_project_folder("~", projects), False)
    check("an empty path may not", g.safe_project_folder("", projects), False)
    link = os.path.join(projects, "sneaky")
    os.symlink(tmp, link)
    check("a symlink out of Projects may not", g.safe_project_folder(link, projects), False)
    check("../ tricks may not", g.safe_project_folder(os.path.join(proj, "..", ".."), projects), False)

    script = os.path.join(proj, "go.sh")
    open(script, "w").write("#!/bin/sh\n# ./go.sh --uninstall removes it\n")
    check("sees a program's own --uninstall", g.own_uninstall(proj, "./go.sh"), "./go.sh --uninstall")
    open(script, "w").write("#!/bin/sh\necho hi\n")
    check("no --uninstall means none", g.own_uninstall(proj, "./go.sh"), "")


# ---- which uninstall command is found, and whether it needs a terminal ----
with tempfile.TemporaryDirectory() as tmp:
    def put(name, text, mode=0o755):
        f = os.path.join(tmp, name)
        open(f, "w").write(text)
        os.chmod(f, mode)
    check("nothing to run -> nothing found", g.own_uninstall(tmp, "./go.sh"), "")
    put("install.sh", "#!/bin/sh\n# ./install.sh --uninstall removes it\n")
    check("install.sh --uninstall is found", g.own_uninstall(tmp, ""), "./install.sh --uninstall")
    put("uninstall.sh", "#!/bin/sh\necho bye\n")
    check("uninstall.sh beats install.sh", g.own_uninstall(tmp, ""), "./uninstall.sh")
    put("go.sh", "#!/bin/sh\n# --uninstall: undo\n")
    check("the run program's --uninstall beats both", g.own_uninstall(tmp, "./go.sh"), "./go.sh --uninstall")
    put("uninstall.sh", "#!/bin/sh\necho bye\n", 0o644)
    check("a non-executable uninstall.sh is not run", g.own_uninstall(tmp, ""), "./install.sh --uninstall")
    put("uninstall.sh", "#!/bin/sh\nsudo bash ./uninstall-system.sh\n")
    check("sudo means it needs a terminal", g.uninstall_needs_terminal(tmp, "./uninstall.sh"), True)
    put("uninstall.sh", "#!/bin/sh\nrm -f ~/.local/share/applications/x.desktop\n")
    check("plain removal does not", g.uninstall_needs_terminal(tmp, "./uninstall.sh"), False)
    put("uninstall.sh", "#!/bin/sh\nread -r -p 'sure? ' a\n")
    check("asking a question needs a terminal", g.uninstall_needs_terminal(tmp, "./uninstall.sh"), True)
    check("a missing script does not", g.uninstall_needs_terminal(tmp, "./nope.sh --uninstall"), False)

print("\nALL OK" if not failed else f"\n{len(failed)} FAILED: {failed}")
sys.exit(1 if failed else 0)
