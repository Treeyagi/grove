# Reference: config, projects, icons and tokens

## Config file

`~/.config/grove/config.json`, mode **0600** because it may hold a GitHub token.

Top-level keys: `tree`, `settings`, `hidden`, `welcomed`, and others added as features land.

## Project fields

A project in `tree` has:

`id`, `name`, `url`, `description`, `path`, `install`, `run`, `private`, `language`, `updated`, `site`, `release`, `tags`

`tags` is a list of lower-case words. Smart groups ("Recently updated", "Has a new release", "Installed, never launched", "Unused for 90 days", one per tag) are built on every `rebuild()` and **never saved**; their ids start with `smart:`.

## Launch history

`~/.config/grove/runs.json` maps project id to the time Grove last launched it. It is its own file so `grove run` can write it while the window is open without the window's next `save()` overwriting it.

## Wishlist

Menu > Import starred repos puts your GitHub stars in a top-level group named `Wishlist` (needs `gh` signed in; uses `gh_ready()`).

## Icon lookup order

First match wins:

1. `~/.config/grove/icons/<name>.svg` or `.png` — the user's own override
2. An `icon`, `logo` or `<name>` image inside the project folder
3. The Canva mascot PNG: `icons/<name>.png` in this repo, listed in `NEW_ICONS`, fetched once by
   `fetch_new_icons()` into `~/.cache/grove/icons/v2/`
4. `BUILTIN_ICONS[name.lower()]` — the offline fallback
5. A coloured letter tile

**To add or change a mascot:** put the PNG in `icons/`, add its name to `NEW_ICONS`, and bump `NEW_ICON_DIR`
(to `v3`, and so on) **if an existing icon changed** — otherwise installed copies keep serving the cached
old one. Built-ins are cached under `~/.cache/grove/icons/`.

## Tokens for private repos

- A pasted fine-grained token is stored as `settings.token` with `settings.token_owner`, and is used **only**
  for that owner's repos.
- `run_async(argv, cb, slug=...)` injects it through `GH_TOKEN`, git's env config, or a 0600 curl config file.
  **Never put a token in `argv`** — the process list is readable by other users on the machine.
- Never print or paste a token in chat.

## GitHub release asset URLs

Two APIs, two different field names, and they are not interchangeable:

- `gh release view --json assets` gives **`apiUrl`**
- The REST API gives **`url`** (metadata) and **`browser_download_url`**

**Private repos need `apiUrl`.**
