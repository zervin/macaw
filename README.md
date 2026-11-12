# linux-stt

Native Debian packaging for [Myna](https://github.com/canonical/myna), Canonical's
offline speech-to-text dictation for the GNOME desktop: press a key, speak, and the
text is typed into the focused app. No snaps.

Status: early. Targets Debian 13 (trixie), GNOME on Wayland.

## Layout

- `myna/`: git submodule of [zervin/myna](https://github.com/zervin/myna), a fork of
  canonical/myna. The `debian-native` branch carries small patches meant to go upstream.
- `debian/`: packaging (in progress).
- `install-user.sh`: development install into `~/.local` with systemd user services.

## Development install

```sh
git clone --recurse-submodules https://github.com/zervin/linux-stt.git
cd linux-stt/myna/client && cargo build --release --locked -p myna-desktop -p myna-hud -p myna-cli
cd ../server && uv sync --extra parakeet
cd ../.. && ./install-user.sh
systemctl --user enable --now myna-server myna-desktop
myna-desktop --install-shortcut '<Super>j'
```

Log out and back in once so GNOME Shell loads the HUD extension, then enable it with
`gnome-extensions enable myna-shell@canonical.com`.

The Parakeet model (about 800 MB) downloads on first start from a pinned URL and is
checked against a SHA-256 hash.

## License

AGPL-3.0-or-later, matching Myna.
