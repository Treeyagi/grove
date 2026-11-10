"""Offline checks for Treeyagi, the buddy: python3 tests/test_buddy.py"""
import json
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import grove as g  # noqa: E402

failed = []


def check(name, got, want):
    good = got == want
    print(("ok   " if good else "FAIL ") + name + ("" if good else f"\n     got  {got!r}\n     want {want!r}"))
    if not good:
        failed.append(name)


BUDDY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "buddy")
info = json.load(open(os.path.join(BUDDY, "atlas.json")))
d = open(os.path.join(BUDDY, "atlas.png"), "rb").read(32)
w, h = struct.unpack(">II", d[16:24])
acts = info["actions"]

check("the atlas is a real PNG", g.valid_png(os.path.join(BUDDY, "atlas.png")), True)
check("every action's frames fit inside the PNG", sorted(n for n, a in acts.items()
      if (a["frames"]) * info["frameWidth"] > w or (a["row"] + 1) * info["frameHeight"] > h), [])
check("every action has one duration per frame", sorted(n for n, a in acts.items() if len(a["ms"]) != a["frames"]), [])
check("no frame is shown for less than 40 ms", sorted(n for n, a in acts.items() if min(a["ms"]) < 40), [])
used = {"idle", "nap", "stretch", "wave", "think", "bee_carry", "victory", "sad_slump", "faint", "lever_pull",
        "dance_disco", "dance_groove", "shrug"} | set(g.FIDGETS)
check("every action Grove plays is in the atlas", sorted(used - set(acts)), [])
check("idle loops (so he never freezes)", acts["idle"]["loop"], True)
check("nap loops", acts["nap"]["loop"], True)
check("bee_carry loops (he keeps carrying while it downloads)", acts["bee_carry"]["loop"], True)

for msg, want in [
    ("Downloading Medllm v0.1.2…", ("busy", "Downloading Medllm v0.1.2…")),
    ("Cloning spare…", ("busy", "Cloning spare…")),
    ("Fetching repos from GitHub…", ("busy", "Fetching repos from GitHub…")),
    ("Downloaded Medllm v0.1.2", ("win", "Downloaded Medllm v0.1.2")),
    ("Cloned grove at v1", ("win", "Cloned grove at v1")),
    ("Added 3 new repos", ("win", "Added 3 new repos")),
    ("Already up to date", ("win", "Already up to date")),
    ("Couldn't download it", ("fail", "Couldn't download it")),
    ("Clone failed", ("fail", "Clone failed")),
    ("Uninstalled Demo: removed 1 start-menu entry.", ("gone", "Uninstalled Demo: removed 1 start-menu entry.")),
    ("Removed Demo", ("gone", "Removed Demo")),
    ("Token removed", None),
    ("", None),
    ("Set a repository URL or folder first", None),
]:
    check(f"mood of {msg!r}", g.buddy_mood(msg), want)

print("\nALL OK" if not failed else f"\n{len(failed)} FAILED: {failed}")
sys.exit(1 if failed else 0)
