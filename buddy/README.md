# Treeyagi's atlas

`atlas.png` and `atlas.json` are the animation frames Grove shows in its bottom strip. They are a small slice of
the **Treeyagi Character Pack v2.9** (the front-facing row of 16 of its 29 actions, cropped to one common box and
palette-reduced). Rebuild with `python3 tools/make_buddy.py /path/to/Treeyagi-Character-Pack-v2.9`.

Grove downloads these two files once from this folder and keeps them in `~/.cache/grove/buddy/v1/`. If you change the art,
bump `v1` in `BUDDY_DIR` (grove.py) so everyone fetches the new one.
