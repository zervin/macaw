# How macaw is built: AI-assisted, in the open

Macaw is written with **Claude Code** (Anthropic) under the direction of its human
maintainer. We say so up front, because you should know how the software you run was
made, and because hiding it would be the less trustworthy choice.

## Who does what

- **The maintainer** decides what to build, sets the requirements, reviews the changes,
  runs everything on real hardware (a Framework 13 AMD laptop on Debian 13), approves
  every commit and release, and is responsible for the result.
- **Claude Code** researches, writes most of the code, packaging and documentation, runs
  the builds and tests, and reviews its own work with independent review passes,
  including the security review that shaped the current CI and release process.
- **Canonical's Myna team** wrote the dictation software itself. Macaw's patches to it
  are small, and each one is offered back upstream.

## How you can tell

- Every commit Claude Code wrote ends with a
  `Co-Authored-By: Claude ... <noreply@anthropic.com>` trailer. We keep them, and you can
  list them with `git log --grep "Co-Authored-By: Claude"`.
- Pull requests from AI agents say so in their description.
- Pull requests are also reviewed by an automated Claude reviewer
  ([.github/workflows/claude-review.yml](.github/workflows/claude-review.yml)), whose
  comments are marked as coming from it. It advises; a human decides.

## What we check so this is not slop

- Builds and tests run in a clean Debian container on every change, using Myna's own Rust
  test suites.
- Releases are built only by CI from a tagged commit, signed, and carry build provenance
  you can verify ([README](README.md#verify-what-you-install)).
- The benchmarks in [bench/](bench/README.md) were run on real recordings, list their
  limits, and come with the tools to repeat them.
- When the AI is wrong, the record says so. For example, a "live reload bug" we
  suspected turned out to be our own mistake about where Myna stores its settings, and the
  correction is in the history.

## Contributing with AI

You are welcome to use AI tools. We ask the same of you as of ourselves:

1. **Say so** in the pull request, and keep any co-author trailers your tool adds.
2. **Understand and test what you submit.** You are responsible for it, not the tool.
3. **Keep changes small and explained**, so a human can review them.

Pull requests that look generated and untested, with no explanation, may be closed
without detailed review. That is about effort, not tools.
