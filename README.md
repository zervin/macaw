# macaw

Macaw is native Debian packaging for [Myna](https://github.com/canonical/myna), Canonical's
offline speech-to-text dictation for the GNOME desktop: press a key, speak, and the
text is typed into the focused app. No snaps.

> **Unofficial.** Macaw builds Canonical's Myna with a few small patches. It is not
> affiliated with or endorsed by Canonical. All of the dictation software is Myna's work;
> report Myna bugs that also happen with the official snaps
> [upstream](https://github.com/canonical/myna/issues), and packaging problems here.

Status: early. Targets Debian 13 (trixie), GNOME on Wayland, amd64.

## Packages

- `myna-desktop`: the dictation daemon (a systemd user service), the HUD and its GNOME
  Shell extension, and the settings schema.
- `myna-server-parakeet`: the local speech recognition backend (NVIDIA Parakeet TDT 0.6B v3,
  int8 on the CPU). The model (about 800 MB) downloads on the service's first start from a
  pinned URL and is checked against a SHA-256 hash.

The package names keep Myna's name because they are Myna. Anything macaw adds of its own
will be named `macaw-*`.

## Install from the apt repository

The repository goes live with the first tagged release. It is signed with the key in
[`macaw-archive-key.asc`](macaw-archive-key.asc), fingerprint
`3142 5706 23DB C5C4 E976  B0F6 11E8 2FCA 6433 F584`.

```sh
curl -fsSL https://zervin.github.io/macaw/macaw-archive-keyring.gpg \
  | sudo tee /usr/share/keyrings/macaw-archive-keyring.gpg >/dev/null
echo "deb [signed-by=/usr/share/keyrings/macaw-archive-keyring.gpg] https://zervin.github.io/macaw trixie main" \
  | sudo tee /etc/apt/sources.list.d/macaw.list
sudo apt update && sudo apt install myna-desktop myna-server-parakeet
myna-desktop --install-shortcut '<Super>j'
```

## Build

```sh
git clone --recurse-submodules https://github.com/zervin/macaw.git
cd macaw && ./build.sh          # debs land in dist/, built in a debian:trixie container
sudo apt install ./dist/myna-desktop_*.deb ./dist/myna-server-parakeet_*.deb
myna-desktop --install-shortcut '<Super>j'
```

Log out and back in once so GNOME Shell loads the extension, then enable it with
`gnome-extensions enable myna-shell@canonical.com`.

`install-user.sh` is an alternative development install into `~/.local`.

## Layout

- `myna/`: git submodule of [zervin/myna](https://github.com/zervin/myna), a fork of
  canonical/myna. Its `debian-native` branch carries every change macaw makes to Myna,
  one commit per change, kept small so they can go upstream.
- `debian/`: the Debian packaging.
- `build.sh`: builds the debs in a clean `debian:trixie` container.
- `ci/`, `.github/workflows/`: CI builds, the apt repository, and the weekly rebase onto
  new upstream releases.

## Changes from upstream Myna

- The GNOME Shell extension also launches a HUD installed by a distro package at
  `/usr/libexec/myna/myna-hud`, not only the snap's.
- Packaging only (not code): no snaps, no Myna Settings app. Settings live in dconf, and
  the backend runs as a plain systemd user service.

## Credits

- **[Myna](https://github.com/canonical/myna)** by Canonical Ltd. and its contributors:
  the dictation client, HUD, GNOME Shell extension, inference server and model tooling.
  AGPL-3.0-or-later.
- **[Murmure](https://github.com/Kieirra/murmure)** by Kieirra: Myna's Parakeet decoding
  loop and adaptive VAD are ported from it (AGPL-3.0), and the int8 model bundle comes from
  [murmure-model](https://github.com/Kieirra/murmure-model).
- **[Parakeet TDT 0.6B v3](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3)** by NVIDIA,
  CC-BY-4.0. ONNX export by
  [istupakov](https://huggingface.co/istupakov/parakeet-tdt-0.6b-v3-onnx), int8 SmoothQuant
  encoder by [Olicorne](https://huggingface.co/Olicorne/parakeet-tdt-0.6b-v3-smoothquant-onnx).
  No model was retrained.
- **[OpenAI Whisper](https://github.com/openai/whisper)** text normalizers (MIT), and
  **[Adwaita](https://gitlab.gnome.org/GNOME/adwaita-icon-theme)** icons by the GNOME
  Project (LGPL-3.0), both included by Myna.
- **[ONNX Runtime](https://github.com/microsoft/onnxruntime)** (MIT) and the Rust and Python
  libraries listed in each package's `/usr/share/doc`.

Each package installs the full license texts and notices in `/usr/share/doc/<package>/`:
`copyright`, `LICENSE`, Myna's `NOTICE`, and `rust-crates-licenses.txt.gz` (myna-desktop) or
`MODEL-NOTICE` (myna-server-parakeet).

## License

AGPL-3.0-or-later, matching Myna. Parts of Myna are AGPL-3.0-only, MIT or LGPL-3.0; see
`debian/copyright`.
