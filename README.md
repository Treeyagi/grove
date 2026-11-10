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

First launch shows a short welcome tour (reopen it from the menu). Tap a project: the one big button says **Get** (downloads and sets it up), then **Open**. Groups are headings you can fold; their ⋯ button renames, moves or deletes them. Everything else is in the two menus at the top.

- Press the refresh button to sync your repos into an "Unsorted" group, then move them into your own groups.
- Every project shows a plain-language summary taken from its README (with a button to read the whole thing),
  and the tree shows a one-line blurb under each name. Use the search box to find a repo by what it does.
- Each project has **Editor, Terminal, Install, Run, Files** and **GitHub** buttons. Install and Run
  commands are detected from the repo (npm, cargo, go, Python, make, `install.sh`) and can be edited.
- Projects deployed to GitHub Pages get a **Live** button, and **Run** opens the live site (no clone needed).
- **Install** and **Run** download the project first if it isn't on your computer yet. Run on a new repo does the
  whole chain in one terminal: get it, install, then run.
- **Releases first.** If the repo has a GitHub release, Grove downloads that instead of the main branch: an
  AppImage, or a Linux x86_64 `.tar.gz`/`.zip` (it skips Windows, Mac, ARM, `.deb` and checksum files),
  unpacked into your projects folder with its executable flags kept. A release with no download gets its source
  cloned at the release's tag. Repos with no release are cloned as before. Turn it off in ☰ → Settings →
  *Download releases*.
- **It works out how to run it.** From the files (npm, cargo, go, Python, make, `install.sh`), from what a release
  contains (an AppImage, `run.sh`/`start.sh`, a `.desktop` file's `Exec=`, or the one program in the folder), and
  otherwise from the README: the first safe command in a code block under an install or run heading, checked
  against the files that are really there (never `sudo`, `curl | sh` or the like). You can still edit both commands.
- **Uninstall.** A project that is on your computer has an **Uninstall…** row. It first runs the project's own
  uninstall if it has one (its run program's `--uninstall`, an executable `uninstall.sh`, or `install.sh --uninstall`;
  one that needs a password opens in a terminal), then removes the start-menu entries (`~/.local/share/applications/*.desktop`) that point into
  the project's folder, and deletes the folder, but only when it is inside your Projects folder. The project stays on
  your list as "Not installed" so you can Get it again. It asks first and shows what will go.
- **Updates.** A project Grove downloaded from a release shows an **Update to vX** button when a newer release
  exists. An update puts the new one in the same folder and keeps the old one beside it (`name.old-<time>`);
  source releases switch to the new tag.
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

## Sharing a private repo

Menu > **Share a private repo…** opens a two-sided wizard.

- **I want to share:** it walks you through making a read-only, expiring GitHub token (fine-grained, "Contents: read-only",
  only the repos you pick), lets you check which repos it opens, and gives you a how-to message to send with it.
- **I was sent a token:** paste it, Grove checks it with GitHub and saves it in a file only you can read
  (`~/.config/grove/`). The shared repos then show up in the tree under the owner's name, and Install, Run and
  release downloads work on them. The token is only sent to GitHub, and only for the repos of the person who shared it;
  your own `gh` login is used for everything else. Remove it any time from the same wizard, or revoke it on GitHub.

## Memory

Grove draws with GTK's plain CPU renderer by default, which keeps it around 90 MB instead of about 240 MB (it never loads the OpenGL stack). To use the GPU renderer instead, start it with `GSK_RENDERER=ngl`.

## Project icons

Every project gets an icon in the list and on its page. Grove picks, in order: your own `~/.config/grove/icons/<name>.svg` (or `.png`), an `icon`/`logo`/`<name>` image in the project's folder, the cartoon mascot for the repos it knows by name (downloaded once from this repo's [`icons/`](icons) folder and kept in the cache), the older built-in drawing of it if you're offline, then a coloured tile with the first letter. The mascots were made with Canva.

## Treeyagi, the buddy

A little animated cartoon of the maker lives in a strip along the bottom of the window. He waves hello, carries a swarm
of bees while something downloads, cheers when it works, slumps when it doesn't, flops over when you uninstall something,
dances (and says something silly) when you click him, and naps if you leave him alone. He also waves from the welcome tour
and the empty home screen. Turn him off in ☰ > *Show Treeyagi* or in Settings. He needs nothing installed: the art is
downloaded once, and without it (or without GdkPixbuf) he just isn't shown.

## Look

Grove has a warm look (cream and cocoa with a coral accent, rounded cards, a friendly round font if Nunito or Quicksand is installed) that follows your system's light or dark setting. The hacker-movie theme is still one switch away in the menu.
