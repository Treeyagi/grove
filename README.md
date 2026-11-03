# Grove

A small GTK4 / libadwaita app for Linux that pulls in your GitHub repos, sorts them into a tree of
groups, and installs, runs and opens them with one click. Comes with a 90s hacker-movie theme
(switch it off from the menu).

## One-line install and run

```bash
curl -fsSL https://raw.githubusercontent.com/Treeyagi/grove/main/install.sh | sh
```

This copies `grove.py` to `~/.local/share/grove`, adds Grove to your app menu and opens it.
Read the [script](install.sh) first if you like; it is short and never uses `sudo`.

Options go after `sh -s --`, for example `... | sh -s -- --no-launch` or `... | sh -s -- --uninstall`.

## Requirements

- Python 3 with GTK4 and libadwaita bindings
  - Arch/CachyOS: `sudo pacman -S --needed python-gobject gtk4 libadwaita`
  - Debian/Ubuntu: `sudo apt install python3-gi gir1.2-gtk-4.0 gir1.2-adw-1`
  - Fedora: `sudo dnf install python3-gobject gtk4 libadwaita`
- [`gh`](https://cli.github.com) signed in (`gh auth login`) to sync and clone your repos

## Using it

- Press the refresh button to sync your repos into an "Unsorted" group, then move them into your own groups.
- Each project has **Editor, Terminal, Install, Run, Files** and **GitHub** buttons. Install and Run
  commands are detected from the repo (npm, cargo, go, Python, make, `install.sh`) and can be edited.
- Install clones the repo first if it is not on disk yet.
- Settings (editor, terminal, projects folder) are in the ☰ menu. Your data lives in `~/.config/grove/config.json`.

Run without installing: `python3 grove.py`
