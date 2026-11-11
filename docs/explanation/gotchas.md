# Why Grove is the way it is: lessons already paid for

Read this before debugging something that looks inexplicable. Each of these cost real time once.

## A `gh` that exists isn't a `gh` that works

`shutil.which("gh")` is not enough to decide whether to use the GitHub CLI. A `gh` that's installed but not
signed in fails **every** command, even against public repos. That's why `gh_ready()` exists: it checks that
`gh` actually works, and Grove falls back to curl and git when it doesn't. Use `gh_ready()` at every new
`gh` call site, not `which`.

## The video background crashed the app

A GTK video background froze or crashed Grove: a `MediaFile` was being freed while the window was drawing or
resizing. It was removed rather than patched. Don't reintroduce video without a design that never destroys a
playing stream.

## Dialogs need a mapped window

`Adw.Dialog.present` requires a window that's already mapped. That's why the first-run welcome dialog is
shown 400 ms after startup rather than immediately.

## The CDN serves stale files for five minutes

`raw.githubusercontent.com` caches for roughly five minutes. The update check and `install.sh` append
`?t=<time>` so a user who updates right after a push gets the new file rather than the cached one.

## Two GitHub APIs, two asset URL fields

`gh release view --json assets` returns `apiUrl`. The REST API returns `url` (metadata) and
`browser_download_url`. **Private repos need `apiUrl`.** Mixing them up gives downloads that 404 only for
private repos, which is easy to miss when testing on a public one.

## "Grove is slow" is probably the graphics driver

On this computer OpenGL falls back to software (`llvmpipe`) whenever the NVIDIA driver and library versions
mismatch, and a reboot fixes it. Check that before investigating a slowness report as a Grove bug.

Related: `GSK_RENDERER=cairo` is set before GTK starts, which cuts memory use from roughly 240 MB to roughly
90 MB. Keep it unless asked.
