# How to push and release Grove

**Ask the user before pushing, releasing, or deleting anything public.** They approve each push.
Local commits don't need approval.

## After a push

Remind the user to pick up the new version, either with the in-app update icon or:

```
curl -fsSL https://raw.githubusercontent.com/Treeyagi/grove/main/install.sh | sh
```

`raw.githubusercontent.com` caches for about five minutes. The update check and `install.sh` append
`?t=<time>` so users aren't served a stale file.

## Privacy status of the owner's repos

Grove lists the user's repos, so it needs to know which are private:
`Medllm`, `cachyos-live-wallpapers`, `Trees-infamous-app`, `spare`, `banana-manager-tools`,
`soundlink-flex-usb-linux`, `Mission-Control`. Grove itself is **public**.

## Release commands for related repos

Separate checkouts, same owner. Each of these should ideally live in its own repo's docs; kept here for now
because Grove installs them.

- **`desktop-buddy`** — `tools/make-executable.sh` → `dist/desktop-buddy.tar.gz`, tag `vX.Y.Z`,
  then `gh release create` with that tarball plus `tools/install-deps.sh`.
- **`Medllm`** — `packaging/make-setup.sh` builds `medllm-lab-setup.tar.gz` from `dist/medllm-lab`.
- **`cachyos-live-wallpapers`** — the root `install.sh` is a chooser; the `collection-*` release holds all wallpapers.
- **`spare-revamp`** — see that repo's own `CLAUDE.md`; Grove's Uninstall button runs its `packaging/uninstall.sh`.
