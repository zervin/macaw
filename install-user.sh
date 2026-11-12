#!/usr/bin/env bash
# Install Myna for the current user on Debian 13 without snaps.
# Builds nothing: run `cargo build --release --locked -p myna-desktop -p myna-hud -p myna-cli`
# in myna/client and `uv sync --extra parakeet` in myna/server first.
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
myna="$here/myna"
bin="$HOME/.local/bin"
data="${XDG_DATA_HOME:-$HOME/.local/share}"
conf="${XDG_CONFIG_HOME:-$HOME/.config}"
units="$conf/systemd/user"

# Client binaries
install -Dm755 -t "$bin" \
    "$myna/client/target/release/myna-desktop" \
    "$myna/client/target/release/myna-hud" \
    "$myna/client/target/release/myna-testbed"

# GSettings schema (GLib also reads $XDG_DATA_HOME/glib-2.0/schemas)
install -Dm644 -t "$data/glib-2.0/schemas" \
    "$myna/client/data/glib-2.0/schemas/com.canonical.Myna.Dictation.gschema.xml"
glib-compile-schemas "$data/glib-2.0/schemas"

# GNOME Shell extension (the HUD host)
ext="$data/gnome-shell/extensions/myna-shell@canonical.com"
rm -rf "$ext"
mkdir -p "$ext"
cp -r "$myna/extensions/myna-shell/"*.js "$myna/extensions/myna-shell/metadata.json" "$ext/"

# The extension only finds the HUD via `snap run` or this override, and it
# must be in gnome-shell's environment (takes effect at next login).
# Never put GSETTINGS_BACKEND here: it would move the whole GNOME session
# off dconf. Only the Myna daemon (its unit) uses the keyfile backend.
mkdir -p "$conf/environment.d"
cat > "$conf/environment.d/60-myna.conf" <<EOF
MYNA_HUD_BINARY=$bin/myna-hud
EOF

# systemd user services
mkdir -p "$units"
cat > "$units/myna-server.service" <<EOF
[Unit]
Description=Myna speech-to-text inference server (Parakeet, CPU)

[Service]
WorkingDirectory=$myna/server
ExecStart=$(command -v uv) run --frozen --extra parakeet myna-server --adapter parakeet --streaming --preload --socket-mode 0600 --socket %t/myna.sock
Restart=on-failure

[Install]
WantedBy=default.target
EOF

cat > "$units/myna-desktop.service" <<EOF
[Unit]
Description=Myna dictation daemon (hotkey, capture, IBus injection)
PartOf=graphical-session.target
After=graphical-session.target myna-server.service
Wants=myna-server.service

[Service]
Environment=GSETTINGS_BACKEND=keyfile
ExecStart=$bin/myna-desktop --socket %t/myna.sock --language en
Restart=on-failure

[Install]
WantedBy=graphical-session.target
EOF

systemctl --user daemon-reload
echo "installed. enable with: systemctl --user enable --now myna-server myna-desktop"
