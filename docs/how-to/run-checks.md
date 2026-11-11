# How to check your work on Grove

## Unit tests

Each of these is standalone, offline, and must end by printing `ALL OK`:

```
python3 tests/test_releases.py
python3 tests/test_uninstall.py
python3 tests/test_icons.py
python3 tests/test_gh.py
python3 tests/test_buddy.py
python3 tests/test_git_update.py
python3 tests/test_smart.py
python3 tests/test_ui_smart.py   # needs a display
```

Add a `check(...)` case for any new pure helper you write.

## Headless UI checks

Build the window in a script, drive it with `GLib.timeout_add`, then quit.

- **Set a distinct `g.APP_ID` before `g.App()`.** Otherwise GTK hands your call off to the user's already-running
  Grove and your script silently does nothing at all.
- Point `XDG_CONFIG_HOME`, `XDG_DATA_HOME` and `XDG_CACHE_HOME` at a temp directory.
- To test against real projects, copy `config.json` into that temp dir. Set `settings.hackers` to false if you
  want to see the warm theme rather than the hackers theme.

## Screenshots

Render the window yourself: `Gtk.WidgetPaintable` → `Gtk.Snapshot` → `renderer.render_texture` → `save_to_png`.

**Do not use `spectacle -a`.** It grabs whichever window has focus — it once captured the user's browser.
If a stray capture happens anyway, delete it.

Take one screenshot before a visual change and one after. Don't re-render to double-check something you've
already verified.

## Background jobs

Use the Bash tool's `run_in_background`. Jobs started with `nohup ... &` were killed when the call ended.
