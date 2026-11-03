<p align="center"><img src="grove.svg" width="140" alt="Grove: the wizard tree"></p>

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
- [`gh`](https://cli.github.com) signed in (`gh auth login`) to sync and clone your repos, **or** no login at all:
  enter a GitHub username in Settings and Grove lists that account's public repos

## Using it

- Press the refresh button to sync your repos into an "Unsorted" group, then move them into your own groups.
- Every project shows a plain-language summary taken from its README (with a button to read the whole thing),
  and the tree shows a one-line blurb under each name. Use the search box to find a repo by what it does.
- Each project has **Editor, Terminal, Install, Run, Files** and **GitHub** buttons. Install and Run
  commands are detected from the repo (npm, cargo, go, Python, make, `install.sh`) and can be edited.
- Projects deployed to GitHub Pages get a **Live** button, and **Run** opens the live site (no clone needed).
- **Install** and **Run** download the repo first if it isn't on your computer yet. Run on a new repo does the
  whole chain in one terminal: clone, install, then run.
- **Remove** a repo with the trash button under the tree, the Delete key, or the button on its page. Grove asks first,
  and for a clone it can also delete the local copy (only a git checkout of that exact repo, with a warning if it
  has uncommitted changes). Removed repos stay gone after a sync; ☰ → *Bring back removed repos* undoes it.
- Settings (editor, terminal, projects folder) are in the ☰ menu. Your data lives in `~/.config/grove/config.json`.

## Whose repos does it show?

- **Treeyagi's public repos are always first.** On every install Grove adds a pinned "Treeyagi" group and keeps it
  fresh in the background, with no login needed.
- **Follow other people:** ☰ → Settings → *Follow other GitHub users*. Each user gets their own group of public repos.
- **Your own repos:** if `gh` is signed in, your repos land in an "Unsorted" group so you can sort them. Turn on
  **Public repos only** to never import private ones.
- Your list lives in `~/.config/grove` on your own computer; nothing is uploaded anywhere.

Run without installing: `python3 grove.py`
