# Grove: architecture and decisions

Grove is a GTK4 / libadwaita desktop app for Linux (CachyOS KDE is the main target). It lists the owner's
GitHub repos and installs, runs and opens them with one big button. Public repo: `Treeyagi/grove`.

Desktop first. The narrow window is a deliberate look, not a phone layout.

## The shape of the app

Everything lives in **one file, `grove.py`** (about 2,500 lines), with no package structure and no build step.
`install.sh` and the in-app update button therefore only have to copy a single file.

Sections inside that file are marked with `# ---- name ---` comments. The full table of what lives where is
[docs/reference/code-map.md](docs/reference/code-map.md).

Supporting folders:

| Folder | What's in it |
|---|---|
| `buddy/` | The sprite atlas for Treeyagi, the animated buddy |
| `icons/` | Mascot PNGs for projects, fetched by installed copies on demand |
| `tests/` | Five standalone offline test scripts, each printing `ALL OK` |
| `tools/` | Helper scripts |

## How the parts fit

**Config.** `~/.config/grove/config.json`, mode 0600, because it may hold a GitHub token.
It holds `{tree, settings, hidden, welcomed, ...}`. Field-level detail is in
[docs/reference/config.md](docs/reference/config.md).

**The one big button** has two modes, and which one you get depends on what's on disk:

- **Get** — `install()`. The project isn't on disk yet, so: `clone()` → `latest_release()` → `_acquire()`
  (download and `unpack` a usable release asset, or fall back to `git clone` at the release tag) →
  `fill_missing()` → `detect_commands()` → run the install step in a terminal.
- **Open** — `run_project()`. The project is installed, so just launch it.
- A project that has an install step but nothing runnable shows **Install** instead of Open.
- **Update** (a newer release) — `update_release()`. A downloaded release is unpacked over a fresh folder (the old one is
  kept as `.old-…`); if the project's install step is `./install.sh`, `_updated()` runs it again in the background,
  without a token or keyboard, and toasts the result. *(2026-11-13)* Installers like MedLLM Lab's copy the program
  to `~/.local/share/…`, so without this the menu entry kept starting the old version. install.sh must never start
  the app; Grove does that.

**Navigation** is an `Adw.NavigationSplitView(collapsed=True)`. The sidebar is the home `ListView` over a
`TreeListModel`, rebuilt by `rebuild()`. Selecting a project sets `show-content`; going back clears the
selection. Groups are section headings that fold on tap, and their ⋯ button opens a group page via `open_group()`.

**Smart groups** are virtual: `smart_items()` builds them from the real tree on every `rebuild()` and prepends them to the store. They hold the same project dicts as the real groups, are flagged `smart`, and are never saved or valid drop targets.

**Command line.** `grove list` and `grove run <name>` are handled by `cli_main()` before GTK starts a window. `grove --quick` goes through `Gio.Application`'s command-line handling so it also reaches an already-open window.

**The look** is three CSS layers loaded in order, later winning: `APP_CSS`, then the warm palette
(`WARM_LIGHT` / `WARM_DARK` / `WARM_CSS`, which override libadwaita's named colours), then `HACKERS_CSS`.

**Icons** resolve by first match from a fixed list of sources, ending in a coloured letter tile so there is
always something to draw. The order and how to add a mascot are in
[docs/reference/config.md](docs/reference/config.md).

**Private repos** use a pasted fine-grained token, stored as `settings.token` with `token_owner`, and used
only for that owner's repos. `run_async(argv, cb, slug=...)` passes it through `GH_TOKEN`, git's env config,
or a 0600 curl config file — **never on the command line**, where other users on the machine could read it
from the process list.

## Decisions, with the reasoning

**One file instead of a package.** Keeps `install.sh` and the self-update path trivial: one file to copy,
nothing to reinstall. The cost is that `grove.py` is too big to read whole, which is why the code map exists.

**`gh_ready()` instead of `shutil.which("gh")`** for deciding whether to use the GitHub CLI. A `gh` that is
installed but not signed in fails *every* command, even on public repos. `gh_ready()` checks it actually
works, and Grove falls back to curl and git when it doesn't. Use it at every new `gh` call site.

**`GSK_RENDERER=cairo`, set before GTK starts.** Drops memory use from roughly 240 MB to roughly 90 MB.
Keep it unless asked otherwise.

**No video background.** A GTK video background froze or crashed the app, because a `MediaFile` was being
freed while the window was drawing or resizing. It was removed. Don't bring it back without a design that
never destroys a playing stream. See [docs/explanation/gotchas.md](docs/explanation/gotchas.md).

**Cache-busting on `raw.githubusercontent.com`.** That host caches for about five minutes, so the update
check and `install.sh` append `?t=<time>` to make sure users get the new file.

## Where to look next

- [docs/reference/code-map.md](docs/reference/code-map.md) — what lives where in `grove.py`
- [docs/reference/config.md](docs/reference/config.md) — config, project fields, icons, tokens
- [docs/how-to/run-checks.md](docs/how-to/run-checks.md) — tests, headless UI checks, screenshots
- [docs/how-to/release.md](docs/how-to/release.md) — pushing and releasing
- [docs/explanation/gotchas.md](docs/explanation/gotchas.md) — hard-won lessons worth reading before debugging
