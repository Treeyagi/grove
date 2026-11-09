# Grove: notes for Claude

GTK4 / libadwaita app for Linux (CachyOS KDE is the main target) that lists GitHub repos and installs, runs and
opens them with one big button. GitHub: Treeyagi/grove (public). Desktop first; the narrow window is a look, not a phone.

## Keep token use low
- **Never read `grove.py` whole** (about 2500 lines). Find things with `grep -n "def name\|# ----" grove.py`, then read that range.
- Line numbers drift; use the section markers (`# ---- name ---`) and function names below.
- Make edits with a small Python patch script that does `assert s.count(old) == 1` before replacing, so a miss fails loudly.
- Don't re-render screenshots to "double check" a change you already verified. One before, one after.
- For a big design choice ask once (AskUserQuestion) instead of building two versions.

## Map (all in `grove.py`, one file so `install.sh` and the update button only copy one thing)
| Where | What |
|---|---|
| top: `APP_CSS`, `WARM_LIGHT/WARM_DARK/WARM_CSS`, `HACKERS_CSS` | Look. Warm palette overrides libadwaita named colours; load order is APP, WARM, HACKERS (later wins) |
| `default_settings`, `new_project`, `walk` | Data model helpers |
| `# ---- releases` : `asset_score`, `pick_asset`, `parse_release`, `unpack` | Choosing and unpacking a release download |
| `release_run`, `readme_commands`, `_deps_step`, `detect_commands` | Work out the install and run commands for a folder |
| `# ---- sharing private repos with a token` | `looks_like_token`, `write_curl_auth`, `summarize_token`, `rest_repo` |
| `is_installed_copy`, `update_available`, `write_update` | Self-update (the header update icon) |
| `class Column`, `grad_class`, `project_icon`, `find_icon`, `BUILTIN_ICONS` | Page layout helper and the icons (see Icons) |
| `class Grove` / `rebuild`, `_selected`, `open_group`, `_on_back` | Home list and navigation |
| `# ---- detail pane` : `show_detail`, `empty_page`, `project_page`, `big_icon` | A project's page, with the one big button |
| `# ---- launching` : `install`, `run_project`, `_launch`, `open_terminal` | What the buttons do |
| `# ---- github` : `run_async`, `sync*`, `clone`, `latest_release`, `_download_release`, `_git_clone` | Talking to GitHub, token handling |
| `show_welcome`, `show_share_wizard`, `show_settings` | Dialogs |

## How things fit
- Config: `~/.config/grove/config.json` (mode 0600, may hold a token). `{tree, settings, hidden, welcomed, ...}`.
  A project has `id, name, url, description, path, install, run, private, language, updated, site, release`.
- **Get** = `install()`: not on disk, so `clone()` -> `latest_release()` -> `_acquire()` (a usable asset is downloaded and
  `unpack`ed, else `git clone` at the release tag) -> `fill_missing()` -> `detect_commands()` -> terminal install step.
  **Open** = `run_project()`. A project with an install step but nothing to run shows **Install** instead.
- Navigation: `Adw.NavigationSplitView(collapsed=True)`. Sidebar = home `ListView` over a `TreeListModel` (`rebuild()`).
  Selecting a project sets `show-content`; back clears the selection. Groups are section headings that fold on tap;
  their ⋯ button opens the group page via `open_group()`.
- Icons, first match wins: `~/.config/grove/icons/<name>.svg|png`, an icon/logo/`<name>` image in the project folder,
  `BUILTIN_ICONS[name.lower()]`, then a coloured letter tile. Built-ins are cached under `~/.cache/grove/icons/`.
- Private repos: a pasted fine-grained token (`settings.token`, `token_owner`) is used only for that owner's repos.
  `run_async(argv, cb, slug=...)` injects it through `GH_TOKEN`, git's env config, or a 0600 curl config file, never argv.
  Never print or paste a token in chat.
- RAM: `GSK_RENDERER=cairo` is set before GTK starts (about 90 MB instead of about 240 MB). Keep it unless asked.

## Check your work
- `python3 tests/test_releases.py` (offline) must end with `ALL OK`. Add a `check(...)` for new pure helpers.
- Headless UI checks: build the window in a script, drive it with `GLib.timeout_add`, then quit. **Set a distinct
  `g.APP_ID`** before `g.App()`, otherwise GTK hands off to the user's running Grove and your script silently does nothing.
  Point `XDG_CONFIG_HOME`, `XDG_DATA_HOME`, `XDG_CACHE_HOME` at a temp dir, and copy `config.json` there if you want real projects
  (set `settings.hackers` false to see the warm theme).
- Screenshots: render the window yourself (`Gtk.WidgetPaintable` -> `Gtk.Snapshot` -> `renderer.render_texture` -> `save_to_png`).
  **Do not use `spectacle -a`**: it grabs whatever window is focused (once it captured the user's browser). Delete any stray capture.
- Background jobs: use the Bash tool's `run_in_background`; `nohup ... &` jobs got killed when the call ended.

## Gotchas already paid for
- `raw.githubusercontent.com` caches for about 5 minutes. The update check and `install.sh` add `?t=<time>` so users get the new file.
- A GTK video background froze or crashed the app (freeing a `MediaFile` while the window draws or resizes). It was removed.
  Don't bring back video without a plan that never destroys a playing stream.
- `Adw.Dialog.present` needs a mapped window: the first-run welcome is shown 400 ms after startup.
- `gh release view --json assets` gives `apiUrl`; the REST API gives `url` (metadata) and `browser_download_url`. Private repos need `apiUrl`.
- This computer's OpenGL is software (`llvmpipe`) while the NVIDIA driver and library versions mismatch; a reboot fixes it. Don't chase "slow" reports before checking that.

## Rules
- Commits end with `Co-Authored-By: Claude <noreply@anthropic.com>` (use the model name from the session reminder).
  If git has no identity in a fresh clone, set a repo-local one (Treeyagi, `83430661+Treeyagi@users.noreply.github.com`).
- **Ask before** pushing, creating releases, or deleting anything public; the user approves each push. Local commits are fine.
- Never commit secrets or tokens. The user's repos `Medllm`, `cachyos-live-wallpapers`, `Trees-infamous-app`, `spare`, `banana-manager-tools`,
  `soundlink-flex-usb-linux`, `Mission-Control` are private.
- After a push, remind the user to re-run `curl -fsSL https://raw.githubusercontent.com/Treeyagi/grove/main/install.sh | sh` (or use the update icon).

## Related repos (separate checkouts, same owner)
- `desktop-buddy`: release = `tools/make-executable.sh` -> `dist/desktop-buddy.tar.gz`, tag `vX.Y.Z`, `gh release create` with it and `tools/install-deps.sh`.
- `Medllm`: `packaging/make-setup.sh` builds `medllm-lab-setup.tar.gz` from `dist/medllm-lab`.
- `cachyos-live-wallpapers`: root `install.sh` is a chooser; the `collection-*` release holds all wallpapers.
- Leftover: the public pre-release `backgrounds-v1` on this repo holds old video files nothing uses. Delete only if the user says so.
