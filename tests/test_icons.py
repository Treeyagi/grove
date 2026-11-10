"""Offline checks for the downloaded mascot icons: python3 tests/test_icons.py"""
import os
import shutil
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


ICONS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "icons")

# every mascot the app knows about is in the repo's icons/ folder, and is a real PNG
check("every name in NEW_ICONS has a file", sorted(n for n in g.NEW_ICONS if not os.path.isfile(os.path.join(ICONS, n + ".png"))), [])
check("every file in icons/ is in NEW_ICONS", sorted(f[:-4] for f in os.listdir(ICONS) if f.endswith(".png") and f[:-4] not in g.NEW_ICONS), [])
check("every file is a valid PNG", sorted(n for n in g.NEW_ICONS if not g.valid_png(os.path.join(ICONS, n + ".png"))), [])
check("every mascot has a built-in fallback", sorted(n for n in g.NEW_ICONS if n not in g.BUILTIN_ICONS), [])

with tempfile.TemporaryDirectory() as tmp:
    g.NEW_ICON_DIR = os.path.join(tmp, "v2")
    os.makedirs(g.NEW_ICON_DIR)
    d = {"name": "Spare", "path": ""}
    check("not downloaded yet: the built-in drawing", g.find_icon(d).endswith(".svg"), True)
    shutil.copy(os.path.join(ICONS, "spare.png"), g.NEW_ICON_DIR)
    check("downloaded: the mascot wins over the built-in", g.find_icon(d), os.path.join(g.NEW_ICON_DIR, "spare.png"))
    check("the name match ignores case", g.find_icon({"name": "SPARE", "path": ""}), os.path.join(g.NEW_ICON_DIR, "spare.png"))
    open(os.path.join(g.NEW_ICON_DIR, "grove.png"), "wb").write(b"<html>404 not found</html>" * 80)
    check("an error page is not an icon", g.new_icon_path("grove"), None)
    open(os.path.join(g.NEW_ICON_DIR, "medllm.png"), "wb").write(b"\x89PNG\r\n\x1a\n" + b"x" * 10)
    check("a truncated file is not an icon", g.new_icon_path("medllm"), None)
    check("a name that has no mascot is not looked up", g.new_icon_path("somethingelse"), None)
    own = os.path.join(tmp, "own")
    os.makedirs(own)
    shutil.copy(os.path.join(ICONS, "grove.png"), os.path.join(own, "icon.png"))
    check("the project's own icon still beats the mascot", g.find_icon({"name": "spare", "path": own}), os.path.join(own, "icon.png"))

print("\nALL OK" if not failed else f"\n{len(failed)} FAILED: {failed}")
sys.exit(1 if failed else 0)
