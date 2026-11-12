#!/usr/bin/env bash
# Build the Myna debs in a clean debian:trixie container.
# Output: dist/*.deb. Usage: ./build.sh [debian-revision, default 1]
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
rev="${1:-1}"
image="${MYNA_BUILD_IMAGE:-debian:trixie}"

# Pinned tools fetched inside the container.
RUST_TOOLCHAIN="$(sed -n 's/^channel = "\(.*\)"/\1/p' "$here/myna/client/rust-toolchain.toml")"
UV_VERSION=0.12.18
UV_SHA256=89eadd7c76fc063887959510d5ba0ab1264dfd5f1143b925ddb73021a40acf16

version="$("$here/myna/dev/version.sh")-$rev"
mkdir -p "$here/dist"

docker run --rm -i \
    -v "$here:/src" -w /src \
    -e VERSION="$version" -e RUST_TOOLCHAIN="$RUST_TOOLCHAIN" \
    -e UV_VERSION="$UV_VERSION" -e UV_SHA256="$UV_SHA256" \
    -e HOST_UID="$(id -u)" -e HOST_GID="$(id -g)" \
    "$image" bash -euo pipefail <<'EOF'
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq --no-install-recommends build-essential devscripts equivs git >/dev/null
mk-build-deps --install --remove --tool 'apt-get -y -qq --no-install-recommends' debian/control >/dev/null

rustup toolchain install "$RUST_TOOLCHAIN" --profile minimal >/dev/null
export RUSTUP_TOOLCHAIN="$RUST_TOOLCHAIN"

curl -fsSL -o /tmp/uv.tgz "https://github.com/astral-sh/uv/releases/download/$UV_VERSION/uv-x86_64-unknown-linux-gnu.tar.gz"
echo "$UV_SHA256  /tmp/uv.tgz" | sha256sum -c - >/dev/null
tar -xzf /tmp/uv.tgz -C /usr/local/bin --strip-components=1
export UV_PYTHON_DOWNLOADS=never UV_CACHE_DIR=/tmp/uv-cache

# Work on a copy (without local build output) so nothing writes into the repo.
rm -rf /build && mkdir /build
tar -C /src --exclude=./dist --exclude=./myna/client/target --exclude=./myna/server/.venv \
    --exclude=./debian/build -cf - . | tar -C /build -xf -
cd /build
git config --global --add safe.directory '*'
cat > debian/changelog <<CL
myna ($VERSION) trixie; urgency=medium

  * Automated build of $(git -C myna rev-parse --short HEAD) from zervin/myna.

 -- zervin <zervin@users.noreply.github.com>  $(date -R)
CL
dpkg-buildpackage -b -us -uc
cp ../*.deb /src/dist/
chown "$HOST_UID:$HOST_GID" /src/dist/*.deb
EOF

ls -la "$here/dist"
