# macaw

Offline dictation for Debian 13: press **Super+J**, speak, press it again, and what you
said is typed wherever your cursor is. Nothing you say leaves your computer.

Macaw packages **[Myna](https://github.com/canonical/myna)**, Canonical's offline
speech-to-text for the GNOME desktop, as ordinary Debian packages, so it runs without
snaps. The dictation software is Myna's; macaw adds packaging and a few small patches
that it offers back upstream.

> **Unofficial.** Not affiliated with or endorsed by Canonical. Report problems with these
> packages [here](https://github.com/zervin/macaw/issues), not to Myna.
>
> **Built with AI, in the open.** This project is written with Claude Code under human
> direction and testing. Every AI-written commit says so. See [AI-ASSISTED.md](AI-ASSISTED.md).

**Status:** early, used daily by its maintainer. Debian 13 (trixie), GNOME on Wayland,
amd64. Other setups may work but are untested.

## Install

You need Debian 13 with GNOME, about 1 GB of disk for the speech model, and sudo.

### Option 1: the install script

Download it, read it (it is short), then run it as yourself, not with sudo:

```sh
curl -fsSLO https://zervin.github.io/macaw/install.sh
less install.sh
sh install.sh
```

It refuses to continue unless the repository key's fingerprint matches the one written
in the script, then installs three packages with apt and sets the Super+J shortcut.

### Option 2: by hand

These are the same steps the script runs.

1. Download the signing key and check its fingerprint. It must be exactly
   `3142 5706 23DB C5C4 E976  B0F6 11E8 2FCA 6433 F584`:

   ```sh
   curl -fsSL https://zervin.github.io/macaw/macaw-archive-key.asc -o macaw.asc
   gpg --show-keys macaw.asc
   ```

2. Install the key and the repository:

   ```sh
   sudo install -d -m 0755 /etc/apt/keyrings
   gpg --dearmor < macaw.asc | sudo tee /etc/apt/keyrings/macaw.gpg >/dev/null
   printf 'Types: deb\nURIs: https://zervin.github.io/macaw\nSuites: trixie\nComponents: main\nSigned-By: /etc/apt/keyrings/macaw.gpg\n' \
     | sudo tee /etc/apt/sources.list.d/macaw.sources
   ```

3. Install the packages and set the shortcut:

   ```sh
   sudo apt update
   sudo apt install myna-desktop myna-server-parakeet myna-config
   myna-desktop --install-shortcut '<Super>j'
   ```

### After installing

1. **Log out and back in once**, so GNOME Shell loads the dictation indicator.
2. The speech model (about 800 MB) **downloads in the background** the first time the
   service starts. An interrupted download resumes. Follow it with
   `journalctl --user -fu myna-server`.
3. Press **Super+J**, speak, press **Super+J** again.
4. Open **Myna Settings** from the app grid to change the shortcut, sounds, when text
   appears, and your **vocabulary**.

**Add your vocabulary.** Names, products and jargon you say often (up to 100) make the
biggest difference to accuracy. In our tests, a personal list cut errors on a
jargon-heavy script from 22% to 9% ([bench/README.md](bench/README.md)). Changes apply
from your next dictation.

Updates come through `sudo apt upgrade`, which restarts the dictation service for you.

## Uninstall

```sh
sh install.sh --uninstall   # remove the packages, the repository and its key
sh install.sh --purge       # also delete the model and your Myna settings
```

By hand: `sudo apt remove myna-desktop myna-server-parakeet myna-config`, delete
`/etc/apt/sources.list.d/macaw.sources` and `/etc/apt/keyrings/macaw.gpg`, and, to free
the space, `~/.cache/myna` (the model) and `~/.config/myna` (your settings).

## What runs and where

| Package | What it is |
|---|---|
| `myna-desktop` | The dictation daemon (a systemd user service), the on-screen indicator and its GNOME Shell extension. |
| `myna-server-parakeet` | Speech recognition on your CPU: NVIDIA's Parakeet TDT 0.6B v3, int8 ONNX, 25 European languages, with punctuation. |
| `myna-config` | Myna Settings. |

**Privacy.** Audio goes from your microphone to the local recognizer over a private
socket (`$XDG_RUNTIME_DIR/myna.sock`, readable only by you). Nothing is sent anywhere.
The only network access is the one-time model download, from a pinned
[GitHub release](https://github.com/Kieirra/murmure-model) checked against a SHA-256 hash.
Each user downloads their own copy into `~/.cache/myna/models`.

**Settings** live in `~/.config/myna/glib-2.0/settings/keyfile`, not in dconf, so plain
`gsettings set` changes nothing Myna reads. Use Myna Settings.

**Services:** `systemctl --user status myna-server myna-desktop`. Both run as you, with
`NoNewPrivileges`.

## Troubleshooting

- **Nothing happens on Super+J:** check `journalctl --user -u myna-desktop` and that the
  server says `server listening` in `journalctl --user -u myna-server`.
- **The first word or two are garbled on some laptops:** the audio chip powers down when
  idle and wakes noisily. See [the note on mic power saving](bench/README.md#what-we-learned).
- **A bug report:** Myna Settings > main menu > Report an Issue opens this project's
  tracker with diagnostics filled in. They include no audio or transcripts.

## Verify what you install

Every release is built by GitHub Actions from a tagged commit of this repository, and each
`.deb` carries a signed [build provenance attestation](https://docs.github.com/en/actions/how-tos/security-for-github-actions/using-artifact-attestations/using-artifact-attestations-to-establish-provenance-for-builds):

```sh
gh attestation verify myna-desktop_*.deb --repo zervin/macaw
```

The apt repository is signed with the key above. Security reports: [SECURITY.md](SECURITY.md).

## Build it yourself

```sh
git clone --recurse-submodules https://github.com/zervin/macaw.git
cd macaw && ./build.sh     # builds and tests in a clean debian:trixie container
sudo apt install ./dist/myna-desktop_*.deb ./dist/myna-server-parakeet_*.deb ./dist/myna-config_*.deb
```

Needs Docker. `install-user.sh` is a development install into `~/.local` instead.

## How it differs from upstream Myna

The changes are on the `debian-native` branch of [zervin/myna](https://github.com/zervin/myna),
one commit per change, so each can be offered upstream:

- The GNOME Shell extension also starts an indicator installed at `/usr/libexec/myna`.
- Myna Settings works on a package install (built with `MYNA_PACKAGING=deb`). It shows the
  installed model, leaves models to apt, keeps settings under `~/.config/myna`, and sends
  bug reports here.
- The model download resumes after an interruption and stops retrying on a bad checksum.

Packaging-only differences: no snaps, no snapd, and the backend runs as a plain systemd
user service.

**Why the packages are still called `myna-*`:** they are Myna, and the name says so. The
app keeps Myna's IDs (`com.canonical.Myna.*`) so settings and the shell extension stay
compatible with upstream. If Canonical would rather we renamed them, we will.

## Benchmarks

On one speaker, one laptop microphone and a script we wrote, so a starting point, not a
general result. Whisper on the GPU (Vulkan) was no more accurate than Parakeet on the CPU
and 4 to 6 times slower. A cloud model (Mistral Voxtral) heard hard words better but
missed names without help. **A personal vocabulary was the biggest improvement.** Details,
caveats and the tools to repeat it on your own voice are in [bench/](bench/README.md).

## Credits

- **[Myna](https://github.com/canonical/myna)** by Canonical Ltd. and contributors: the
  dictation client, indicator, shell extension, settings app, inference server and model
  tooling. AGPL-3.0-or-later.
- **[Murmure](https://github.com/Kieirra/murmure)** by Kieirra: Myna's Parakeet decoding
  loop and voice activity detection are ported from it (AGPL-3.0), and the int8 model
  bundle comes from [murmure-model](https://github.com/Kieirra/murmure-model).
- **[Parakeet TDT 0.6B v3](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3)** by NVIDIA,
  CC-BY-4.0. ONNX export by
  [istupakov](https://huggingface.co/istupakov/parakeet-tdt-0.6b-v3-onnx), int8 SmoothQuant
  encoder by [Olicorne](https://huggingface.co/Olicorne/parakeet-tdt-0.6b-v3-smoothquant-onnx).
  No model was retrained.
- **[OpenAI Whisper](https://github.com/openai/whisper)** text normalizers (MIT) and
  **[Adwaita](https://gitlab.gnome.org/GNOME/adwaita-icon-theme)** icons (LGPL-3.0), both
  included by Myna; **[ONNX Runtime](https://github.com/microsoft/onnxruntime)** (MIT); and
  the Rust and Python libraries listed in each package's `/usr/share/doc`.

Each package installs its license texts and notices under `/usr/share/doc/<package>/`.

## License and source

AGPL-3.0-or-later, matching Myna; parts are AGPL-3.0-only, MIT or LGPL-3.0 (see
`debian/copyright`). The complete source of every published package is this repository at
the release's tag, with the `myna` submodule at the commit that tag records.

Contributing, including how AI-assisted contributions work: [CONTRIBUTING.md](CONTRIBUTING.md).
