#!/bin/sh
# shellcheck disable=SC2086,SC1091 # package lists split on spaces on purpose
# macaw installer: Myna dictation on Debian 13 from the macaw apt repository.
#
# Read this before you run it. It is short, and it does only what the README's
# manual steps do:
#
#   1. Downloads the repository signing key and refuses to continue unless its
#      fingerprint is exactly KEY_FINGERPRINT below.
#   2. Adds the repository (/etc/apt/sources.list.d/macaw.sources), signed-by
#      that key only (/usr/share/keyrings/macaw-archive-keyring.gpg).
#   3. Installs myna-desktop, myna-server-parakeet and myna-config with apt,
#      and macaw-archive-keyring, which keeps that key file current.
#   4. Sets the dictation shortcut (Super+J) for you, the user running it.
#
# Root is used only through sudo, for steps 2 and 3. Nothing is piped into a
# shell. Undo with --uninstall (packages, repository, key) or --purge (also
# the downloaded model and your Myna settings).
#
#   sh install.sh [--uninstall | --purge] [--yes]
set -eu

REPO_URL=https://zervin.github.io/macaw
SUITE=trixie
KEY_URL="$REPO_URL/macaw-archive-key.asc"
KEY_FINGERPRINT=3142570623DBC5C4E976B0F611E82FCA6433F584
KEYRING=/usr/share/keyrings/macaw-archive-keyring.gpg
SOURCES=/etc/apt/sources.list.d/macaw.sources
PACKAGES="myna-desktop myna-server-parakeet myna-config macaw-archive-keyring"

say() { printf '\033[1m==>\033[0m %s\n' "$*"; }
die() { printf 'error: %s\n' "$*" >&2; exit 1; }

mode=install
assume_yes=
for arg in "$@"; do
    case "$arg" in
        --uninstall) mode=uninstall ;;
        --purge) mode=purge ;;
        --yes|-y) assume_yes=-y ;;
        -h|--help) sed -n '3,19p' "$0"; exit 0 ;;
        *) die "unknown option: $arg (try --help)" ;;
    esac
done

[ "$(id -u)" -ne 0 ] || die "run this as yourself, not root: it uses sudo where it needs to"
command -v sudo >/dev/null || die "sudo is required"

confirm() {
    [ -n "$assume_yes" ] && return 0
    printf '%s [y/N] ' "$1"
    read -r answer
    case "$answer" in y|Y|yes|YES) return 0 ;; *) exit 1 ;; esac
}

remove_repo() {
    say "Removing the macaw repository and its key"
    sudo rm -f "$SOURCES" "$KEYRING" /etc/apt/sources.list.d/macaw.list /etc/apt/keyrings/macaw.gpg
}

if [ "$mode" != install ]; then
    confirm "Remove $PACKAGES and the macaw repository?"
    say "Removing packages"
    sudo apt-get remove $assume_yes $PACKAGES || true
    remove_repo
    if [ "$mode" = purge ]; then
        cache="${XDG_CACHE_HOME:-$HOME/.cache}/myna"
        config="${XDG_CONFIG_HOME:-$HOME/.config}/myna"
        say "Deleting the downloaded model ($cache) and your Myna settings ($config)"
        rm -rf "$cache" "$config"
        say "Other users' models and settings are in their own home directories."
    fi
    say "Done. The Super+J shortcut, if set, is in GNOME Settings > Keyboard > Custom Shortcuts."
    exit 0
fi

# --- install ---------------------------------------------------------------

. /etc/os-release
if [ "${ID:-}" != debian ] || [ "${VERSION_ID:-}" != 13 ]; then
    say "This targets Debian 13 (trixie); this system is ${PRETTY_NAME:-unknown}."
    confirm "Continue anyway?"
fi
[ "$(dpkg --print-architecture)" = amd64 ] || die "only amd64 packages are published"
if command -v snap >/dev/null && snap list myna >/dev/null 2>&1; then
    say "The Myna snap is installed too. Both answer the same shortcut; remove one (sudo snap remove myna)."
fi

need=
command -v curl >/dev/null || need="$need curl"
command -v gpg >/dev/null || need="$need gpg"
if [ -n "$need" ]; then
    say "Installing:$need"
    sudo apt-get install $assume_yes --no-install-recommends $need
fi

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

say "Downloading the signing key from $KEY_URL"
curl -fsSL "$KEY_URL" -o "$tmp/key.asc"
found=$(gpg --show-keys --with-colons "$tmp/key.asc" | awk -F: '$1=="fpr"{print $10; exit}')
[ "$found" = "$KEY_FINGERPRINT" ] ||
    die "the key's fingerprint is $found, not $KEY_FINGERPRINT; not trusting it"
say "Key fingerprint matches $KEY_FINGERPRINT"
gpg --dearmor < "$tmp/key.asc" > "$tmp/macaw.gpg"

confirm "Add the macaw repository and install $PACKAGES?"
# Earlier installs used these paths; one source per repository.
sudo rm -f /etc/apt/sources.list.d/macaw.list /etc/apt/keyrings/macaw.gpg
# The keyring package takes this file over once installed.
sudo install -m 0644 "$tmp/macaw.gpg" "$KEYRING"
cat > "$tmp/macaw.sources" <<EOF
Types: deb
URIs: $REPO_URL
Suites: $SUITE
Components: main
Architectures: amd64
Signed-By: $KEYRING
EOF
sudo install -m 0644 "$tmp/macaw.sources" "$SOURCES"

say "Installing $PACKAGES"
sudo apt-get update
sudo apt-get install $assume_yes $PACKAGES

if [ -n "${DBUS_SESSION_BUS_ADDRESS:-}" ]; then
    say "Setting the dictation shortcut to Super+J"
    myna-desktop --install-shortcut '<Super>j' || say "Set it later in Myna Settings."
    gnome-extensions enable myna-shell@canonical.com 2>/dev/null || true
fi

cat <<EOF

Installed. Next:

  1. Log out and back in once, so GNOME Shell loads the dictation indicator.
     On Xfce or KDE Plasma (untested), open Myna Settings after that: it
     sets up IBus, which Myna types through, and the shortcut.
  2. The speech model (about 800 MB) downloads in the background on first
     start. Follow it with:  journalctl --user -fu myna-server
  3. Press Super+J, speak, press Super+J again. The text is typed where your
     cursor is.
  4. Open "Myna Settings" to change the shortcut, sounds, or the vocabulary of
     names and terms you say often.

Problems: https://github.com/zervin/macaw/issues
EOF
