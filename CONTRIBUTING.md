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
answers `@claude` in issues and pull requests. It is advisory only. When something needs a
human decision, such as security, licensing or a release, it labels the issue or pull
request `needs-human`, and the maintainer decides.

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

1. **Upstream updates** arrive as a pull request from the weekly `upstream-sync` job
   (`Update myna to upstream vX.Y.Z`), with the rebased patches on the fork's
   `sync/vX.Y.Z` branch. Read upstream's changes, check that CI passes, then merge.
2. Move the fork's `debian-native` branch to the merged commit:
   `git -C myna push origin HEAD:debian-native`. That is a fast-forward unless the rebase
   rewrote it; the `sync/` branch keeps the old commits reachable either way.
3. Tag and push: `git tag v<myna version>-<YYYYMMDD> && git push origin --tags`. The tag
   builds, attests, creates the GitHub release, and publishes the signed apt repository.
4. On a machine with the repository installed, run `sudo apt update && sudo apt upgrade`,
   and check that `systemctl --user status myna-server myna-desktop` shows both restarted.
