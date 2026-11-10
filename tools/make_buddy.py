#!/usr/bin/env python3
"""Packs the few Treeyagi animations Grove uses into one small atlas (buddy/atlas.png + buddy/atlas.json).

    python3 tools/make_buddy.py /path/to/Treeyagi-Character-Pack-v2.9

Only the front-facing (S) row of each chosen action is used. Every frame is cropped to the same box (the union of what
is drawn in any of them), so the character doesn't jump between actions, and the PNG is palette-reduced to stay small.
Atlas layout: one row per action, frames left to right. atlas.json says which row, how many frames, how long each shows."""
import json
import os
import sys

from PIL import Image

ACTIONS = ["idle", "wave", "victory", "sad_slump", "shrug", "think", "nap", "bee_carry", "dance_disco", "dance_groove",
           "faint", "lever_pull", "stretch", "talk", "meditate", "hurt"]


def main(pack, out):
    meta = json.load(open(os.path.join(pack, "treeyagi.character.json")))["animations"]
    sheets, box = {}, None
    for a in ACTIONS:
        m = meta[a]
        fw, fh, n = m["frameWidth"], m["frameHeight"], m["frameCount"]
        sheet = Image.open(os.path.join(pack, m["actionSheet"])).convert("RGBA")
        frames = [sheet.crop((i * fw, 0, i * fw + fw, fh)) for i in range(n)]     # row 0 = S, facing the viewer
        sheets[a] = (frames, m)
        for f in frames:
            b = f.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox()
            if b:
                box = b if box is None else (min(box[0], b[0]), min(box[1], b[1]), max(box[2], b[2]), max(box[3], b[3]))
    w, h = box[2] - box[0], box[3] - box[1]
    atlas = Image.new("RGBA", (max(len(s[0]) for s in sheets.values()) * w, len(ACTIONS) * h), (0, 0, 0, 0))
    info = {"frameWidth": w, "frameHeight": h, "actions": {}}
    for row, a in enumerate(ACTIONS):
        frames, m = sheets[a]
        ms = [max(40, int(round(f["durationMs"]))) for f in m["directions"]["S"]]
        for i, fr in enumerate(frames):
            atlas.paste(fr.crop(box), (i * w, row * h))
        info["actions"][a] = {"row": row, "frames": len(frames), "ms": ms, "loop": bool(m.get("loop")),
                              "hold": bool(m.get("holdLastFrame"))}
    os.makedirs(out, exist_ok=True)
    q = atlas.quantize(colors=224, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE)
    q.save(os.path.join(out, "atlas.png"), optimize=True)
    json.dump(info, open(os.path.join(out, "atlas.json"), "w"), indent=1)
    print(f"{len(ACTIONS)} actions, frame {w}x{h}, atlas {atlas.size}, {os.path.getsize(os.path.join(out, 'atlas.png')) // 1024} KB")


if __name__ == "__main__":
    main(sys.argv[1], os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "buddy"))
