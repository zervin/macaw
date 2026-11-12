#!/usr/bin/env python3
"""Write the license texts of every third-party Rust crate the client
workspace resolves for Linux, for shipping next to statically linked binaries.

Usage: rust-licenses.py <client-dir> <output-file>
"""

import json
import subprocess
import sys
from pathlib import Path

MIT_TEXT = """\
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""


def fallback(p: dict) -> str:
    """The crate ships no license file: state its declared license in full."""
    lic = p.get("license") or ""
    authors = ", ".join(p.get("authors") or []) or f"the {p['name']} authors"
    text = "(the crate ships no license file; text supplied for its declared license)\n"
    if "MIT" in lic:
        text += f"\n--- MIT ---\nCopyright (c) {authors}\n\n{MIT_TEXT}"
    if "Apache-2.0" in lic:
        text += ("\n--- Apache-2.0 ---\nCopyright the "
                 f"{p['name']} authors ({authors}). Licensed under the Apache License,\n"
                 "Version 2.0; the full text is in /usr/share/common-licenses/Apache-2.0.\n")
    return text


client, out = Path(sys.argv[1]), Path(sys.argv[2])
meta = json.loads(
    subprocess.check_output(
        ["cargo", "metadata", "--format-version", "1", "--locked",
         "--filter-platform", "x86_64-unknown-linux-gnu"],
        cwd=client,
    )
)
workspace = set(meta["workspace_members"])
resolved = {n["id"] for n in meta["resolve"]["nodes"]}
packages = sorted(
    (p for p in meta["packages"] if p["id"] in resolved and p["id"] not in workspace),
    key=lambda p: (p["name"], p["version"]),
)

parts = [
    "Third-party Rust crates statically linked into myna-desktop and myna-hud\n"
    "=========================================================================\n"
]
for p in packages:
    root = Path(p["manifest_path"]).parent
    files = sorted(
        f for f in root.iterdir()
        if f.is_file() and f.name.upper().startswith(("LICENSE", "LICENCE", "COPYING", "NOTICE"))
    )
    parts.append(f"\n{'-' * 72}\n{p['name']} {p['version']}  ({p.get('license') or 'see files'})\n")
    if p.get("repository"):
        parts.append(f"{p['repository']}\n")
    for f in files:
        parts.append(f"\n--- {f.name} ---\n{f.read_text(errors='replace').strip()}\n")
    if not files:
        parts.append(fallback(p))

out.write_text("".join(parts))
print(f"{len(packages)} crates -> {out}")
