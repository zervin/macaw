#!/usr/bin/env bash
# Build a signed flat-ish apt repository (dists/trixie/main) from a directory
# of debs. Keeps every release already published on Pages so older versions
# stay installable. Usage: ci/apt-repo.sh <debs-dir> <out-dir>
# Needs APT_SIGNING_KEY: an ASCII-armored private key without passphrase.
set -euo pipefail

debs="$1"
out="$2"
suite=trixie
pages_url="${PAGES_URL:-https://zervin.github.io/macaw}"

sudo apt-get install -y -qq --no-install-recommends apt-utils gnupg >/dev/null

mkdir -p "$out/pool/main"
# Pull the debs already published, so the index keeps old versions.
if curl -fsSL "$pages_url/dists/$suite/main/binary-amd64/Packages" -o /tmp/old-Packages; then
    sed -n 's/^Filename: //p' /tmp/old-Packages | while read -r f; do
        curl -fsSL "$pages_url/$f" -o "$out/$f" || echo "warn: could not fetch $f"
    done
fi
cp "$debs"/*.deb "$out/pool/main/"

cd "$out"
mkdir -p "dists/$suite/main/binary-amd64"
apt-ftparchive packages pool > "dists/$suite/main/binary-amd64/Packages"
gzip -9kf "dists/$suite/main/binary-amd64/Packages"
apt-ftparchive \
    -o "APT::FTPArchive::Release::Origin=macaw" \
    -o "APT::FTPArchive::Release::Label=macaw" \
    -o "APT::FTPArchive::Release::Suite=$suite" \
    -o "APT::FTPArchive::Release::Codename=$suite" \
    -o "APT::FTPArchive::Release::Architectures=amd64" \
    -o "APT::FTPArchive::Release::Components=main" \
    release "dists/$suite" > "dists/$suite/Release"

export GNUPGHOME="$(mktemp -d)"
printf '%s\n' "$APT_SIGNING_KEY" | gpg --batch --import 2>/dev/null
gpg --batch --yes --armor --detach-sign -o "dists/$suite/Release.gpg" "dists/$suite/Release"
gpg --batch --yes --clearsign -o "dists/$suite/InRelease" "dists/$suite/Release"
gpg --export > macaw-archive-keyring.gpg
rm -rf "$GNUPGHOME"
