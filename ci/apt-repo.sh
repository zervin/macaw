#!/usr/bin/env bash
# Build the signed apt repository (dists/trixie/main) from a directory of
# debs, keeping every release already published on Pages so older versions
# stay installable. Usage: ci/apt-repo.sh <debs-dir> <out-dir>
# Needs APT_SIGNING_KEY: an ASCII-armored private key without passphrase.
#
# Nothing is re-signed on trust: the published InRelease must verify against
# the key in this repository, the Packages index must match the hash it
# signs, and each old deb must match the hash in that index.
set -euo pipefail

debs="$1"
out="$2"
suite=trixie
pages_url="${PAGES_URL:-https://zervin.github.io/macaw}"
here="$(cd "$(dirname "$0")/.." && pwd)"

sudo apt-get install -y -qq --no-install-recommends apt-utils gnupg >/dev/null

old="$(mktemp -d)"
gpg --dearmor < "$here/macaw-archive-key.asc" > "$old/keyring.gpg"
mkdir -p "$out/pool/main"

if curl -fsSL "$pages_url/dists/$suite/InRelease" -o "$old/InRelease"; then
    gpgv --keyring "$old/keyring.gpg" --output "$old/Release" "$old/InRelease"
    curl -fsSL "$pages_url/dists/$suite/main/binary-amd64/Packages" -o "$old/Packages"
    want=$(awk '/^SHA256:/{s=1;next} /^[^ ]/{s=0} s && $3=="main/binary-amd64/Packages"{print $1}' "$old/Release")
    have=$(sha256sum "$old/Packages" | cut -d' ' -f1)
    if [ -z "$want" ] || [ "$want" != "$have" ]; then
        echo "published Packages does not match its signed Release" >&2
        exit 1
    fi
    # Filename and SHA256 of each published deb, one pair per stanza.
    awk '/^Filename: /{f=$2} /^SHA256: /{h=$2} /^$/{if(f)print f, h; f=h=""} END{if(f)print f, h}' \
        "$old/Packages" | while read -r f sum; do
        case "$f" in
            pool/main/*.deb) ;;
            *) echo "refusing published path: $f" >&2; exit 1 ;;
        esac
        case "$f" in */../*|*/./*) echo "refusing published path: $f" >&2; exit 1 ;; esac
        curl -fsSL "$pages_url/$f" -o "$out/$f"
        echo "$sum  $out/$f" | sha256sum -c --quiet - || {
            echo "published $f does not match its signed index" >&2
            exit 1
        }
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
# Keep gpg's messages (never the key) so a failed import can be diagnosed.
printf '%s\n' "$APT_SIGNING_KEY" | gpg --batch --import 2>&1 | grep -v -i 'secret key' || true
gpg --batch --yes --armor --detach-sign -o "dists/$suite/Release.gpg" "dists/$suite/Release"
gpg --batch --yes --clearsign -o "dists/$suite/InRelease" "dists/$suite/Release"
gpg --export > macaw-archive-keyring.gpg
cp "$here/macaw-archive-key.asc" macaw-archive-key.asc
cp "$here/install.sh" install.sh
rm -rf "$GNUPGHOME" "$old"
