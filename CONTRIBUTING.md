# Contributing

Thanks for helping. Macaw is small, so the process is light.

## Where things go

- **A problem with these packages** (installing, upgrading, services, Myna Settings on a
  package install): [open an issue here](https://github.com/zervin/macaw/issues/new?template=report.yml).
  Myna Settings > Report an Issue fills in the diagnostics for you.
- **A bug in Myna that also happens with the official snaps:** report it
  [upstream](https://github.com/canonical/myna/issues).
- **A security problem:** see [SECURITY.md](SECURITY.md). Do not open a public issue.

## Changes

- **Packaging, CI, docs:** a pull request against `main` here.
- **Changes to Myna's code:** a pull request against the `debian-native` branch of
  [zervin/myna](https://github.com/zervin/myna), one commit per change, written so it can
  go upstream. Follow Myna's own `AGENTS.md` and `.kb/` rules. Upstream changes it would
  accept are better sent to [canonical/myna](https://github.com/canonical/myna) directly.

Every pull request builds the debs and runs Myna's Rust tests in a clean Debian container.
To run the same build locally, run `./build.sh` (needs Docker).

**AI tools are welcome.** Say so in the pull request, keep co-author trailers, and test
what you submit. See [AI-ASSISTED.md](AI-ASSISTED.md).

## Reviews

An automated Claude reviewer comments on pull requests from people with write access, and
answers `@claude` in issues and pull requests. It never approves or merges. When something
needs a human decision, such as a bug, security, licensing, workflows or a release, or when
it could not see the changed code, it labels the issue or pull request `needs-human`, and
the maintainer decides.

A pull request the reviewer did not label, and Dependabot's hash-pinned bumps, get GitHub
auto-merge (squash): they merge once the required checks on `main` pass. Adding
`needs-human` by hand turns auto-merge off. If the review did not run, nothing is queued.
Upstream `sync/` pull requests never auto-merge: merging one releases (see Releasing).
Neither do other changes under `.github/`: the reviewer cannot review its own workflow.
Other merges publish nothing; only a `v*` tag releases.

## Model packages

Each speech model is its own package, `myna-server-<family>`, where
`<family>` is one of Myna's model families (`parakeet`, `whisper`, `funasr`).
Only one is installed at a time: every model package has
`Provides`, `Conflicts` and `Replaces: myna-server`, so
`sudo apt install myna-server-whisper` swaps out Parakeet. A model package
ships:

- `/usr/libexec/myna/myna-server-<family>`, an executable that runs the server
  on `$XDG_RUNTIME_DIR/myna.sock`. Myna Settings lists a model by this file.
- the `myna-server` user unit that starts it (`dh_installsystemduser --name=myna-server`).
- `/usr/share/myna/engines/<family>.json`, the engine it runs on, in the
  format of Myna's `modelctl engines`, for example
  `{"active-engine":"cpu","engines":[{"name":"cpu","compatible":true}]}`.
  Without it Settings shows no engine.

## Releasing (maintainers)

1. **Upstream updates** arrive as a pull request from the `upstream-sync` job, which checks
   canonical/myna every six hours (`Update myna to upstream vX.Y.Z`). The rebased patches
   are on the fork's `sync/vX.Y.Z` branch, and the upstream tag is pushed to the fork.
   The Claude reviewer reads the submodule's changes. Read upstream's changes, check that
   CI passes, then merge.
2. The merge runs `upstream-release`, which moves the fork's `debian-native` branch to the
   merged commit (keeping a rewritten old tip as tag `archive/debian-native-<sha>`), then
   tags `v<myna version>-<YYYYMMDD>`. The tag builds, attests, creates the GitHub release,
   and publishes the signed apt repository.
3. A packaging-only release (no submodule change) is tagged by hand:
   `git tag -a v<myna version>-<YYYYMMDD> -m ... && git push origin --tags`.
4. On a machine with the repository installed, run `sudo apt update && sudo apt upgrade`,
   and check that `systemctl --user status myna-server myna-desktop` shows both restarted.
