# Security

## Reporting a vulnerability

Please report privately through GitHub:
**[Report a vulnerability](https://github.com/zervin/macaw/security/advisories/new)**.
Do not open a public issue. You should get a reply within a week.

In scope: the packages from this repository, the apt repository and its signing, the
install script, and the CI and release process. Vulnerabilities in Myna itself that
also affect the official snaps belong
[upstream](https://github.com/canonical/myna/security); if unsure, report here and we
will pass it on.

## What you can verify

- **The apt repository** is signed with the key
  `3142 5706 23DB C5C4 E976  B0F6 11E8 2FCA 6433 F584` (Ed25519, expires 2031-11-11, to be
  extended before then). The install script refuses any other key.
- **Each release's `.deb` files** carry a build provenance attestation, signed by GitHub
  Actions, tying them to the commit and workflow that built them:
  `gh attestation verify <file>.deb --repo zervin/macaw`.
- **The speech model** downloads from a pinned URL and is checked against a SHA-256 hash
  before use (`myna/dev/parakeet/fetch_parakeet_onnx.py`).

## How releases are protected

- Only a `v*` tag publishes, and only the release job can write. That job runs in the
  `github-pages` environment, which holds the signing key, and runs no build code.
- The build job has a read-only token and keeps no credentials while third-party build
  scripts run.
- Third-party actions are pinned to full commit hashes, the build container to a digest,
  and Python and Rust dependencies to hashes or lock files. Dependabot proposes updates.
- New upstream Myna releases arrive as pull requests for a human to review, never as
  automatic releases.
- Before re-signing old packages, CI checks the published index against the signing key
  and each old package against its recorded hash.

The services run as your user with `NoNewPrivileges`. The recognizer listens only on a
Unix socket in your runtime directory, readable only by you.
