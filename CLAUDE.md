# Grove: notes for Claude

GTK4 / libadwaita app for Linux (CachyOS KDE is the main target) that lists GitHub repos and installs, runs
and opens them with one big button. GitHub: `Treeyagi/grove` — **public**, so be doubly careful with secrets.
Desktop first; the narrow window is a look, not a phone.

General working rules (plain English, plan first, git and secrets) are in `~/.claude/CLAUDE.md`.

## Read these before you touch anything

| Before you... | Read first |
|---|---|
| edit **`grove.py`** at all | [docs/reference/code-map.md](docs/reference/code-map.md) — it's ~2,500 lines; **never read it whole** |
| change config, project fields, icons or token handling | [docs/reference/config.md](docs/reference/config.md) |
| run tests, headless UI checks or take screenshots | [docs/how-to/run-checks.md](docs/how-to/run-checks.md) |
| push, release, or touch a related repo | [docs/how-to/release.md](docs/how-to/release.md) |
| debug anything that looks inexplicable | [docs/explanation/gotchas.md](docs/explanation/gotchas.md) — read it **before** investigating, not after |
| make a structural or design decision | [ARCHITECTURE.md](ARCHITECTURE.md) — how it fits together and why |

Add new knowledge to the quadrant that fits ([docs/README.md](docs/README.md)), not to this file.

## Non-negotiables

These cause real damage, so they stay here rather than in a doc:

- **Never read `grove.py` whole.** `grep -n "def name\|# ---- "` then read that range. Line numbers drift —
  navigate by section markers and function names.
- **Patch with an assert.** Use a small Python script that checks `s.count(old) == 1` before replacing,
  so a miss fails loudly instead of editing the wrong place.
- **Never put a token in `argv`** (the process list is world-readable) and never print or paste one in chat.
  Use `run_async(..., slug=...)`, which injects it safely.
- **Use `gh_ready()`, not `shutil.which("gh")`**, at every new `gh` call site. An installed-but-signed-out
  `gh` fails every command, even on public repos.
- **Set a distinct `g.APP_ID` before `g.App()`** in any test script, or GTK hands off to the user's running
  Grove and your script silently does nothing.
- **Never use `spectacle -a`.** It grabs whatever window has focus; it once captured the user's browser.
  Render the window yourself instead (see the run-checks doc).
- **Keep `GSK_RENDERER=cairo`** unless asked. It's the difference between ~90 MB and ~240 MB of RAM.
- Tests live in `tests/`, are offline, and each must print `ALL OK`.
- For a big design choice, ask once with AskUserQuestion instead of building two versions.
