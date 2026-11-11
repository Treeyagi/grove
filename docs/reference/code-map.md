# Code map: what lives where in `grove.py`

Everything is in `grove.py`. **Line numbers drift**, so navigate by the `# ---- name ---` section markers
and the function names below: `grep -n "def pick_asset\|# ---- releases" grove.py`, then read that range.

| Where | What |
|---|---|
| top: `APP_CSS`, `WARM_LIGHT/WARM_DARK/WARM_CSS`, `HACKERS_CSS` | The look. The warm palette overrides libadwaita named colours; load order is APP, WARM, HACKERS (later wins) |
| `default_settings`, `new_project`, `walk` | Data model helpers |
| `# ---- releases`: `asset_score`, `pick_asset`, `parse_release`, `unpack` | Choosing and unpacking a release download |
| `release_run`, `readme_commands`, `_deps_step`, `detect_commands` | Working out the install and run commands for a folder |
| `# ---- sharing private repos with a token`: `looks_like_token`, `write_curl_auth`, `summarize_token`, `rest_repo` | Token handling for private repos |
| `is_installed_copy`, `update_available`, `write_update` | Self-update, behind the header update icon |
| `git_behind_count`, `git_fast_forward`, `check_git_update`, `update_git` | Updating plain git clones (no release): how far behind GitHub, and a safe fast-forward |
| `class Column`, `grad_class`, `project_icon`, `find_icon`, `BUILTIN_ICONS` | Page layout helper and the icons |
| `class Grove` / `rebuild`, `_selected`, `open_group`, `_on_back` | Home list and navigation |
| `# ---- detail pane`: `show_detail`, `empty_page`, `project_page`, `big_icon` | A project's page, with the one big button |
| `# ---- uninstalling`: `confirm_uninstall`, `uninstall`, `start_menu_entries`, `safe_project_folder` | Start-menu entries pointing into a project folder, safe folder deletion, the project's own `--uninstall` |
| `# ---- Treeyagi, the buddy`: `buddy_mood`, `buddy_data`, `Buddy`, `BuddyBar`, `fetch_buddy`, `update_buddy` | The animated buddy: toast text → reaction, the atlas in `buddy/`, the strip under the toasts |
| `# ---- launching`: `install`, `run_project`, `_launch`, `open_terminal` | What the buttons actually do |
| `# ---- github`: `run_async`, `sync*`, `clone`, `latest_release`, `_download_release`, `_git_clone` | Talking to GitHub, token injection |
| `show_welcome`, `show_share_wizard`, `show_settings` | Dialogs |

## Editing safely

Make edits with a small Python patch script that asserts `s.count(old) == 1` before replacing, so a miss
fails loudly instead of silently patching the wrong place.
