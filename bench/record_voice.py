#!/usr/bin/env python3
"""Record the personal voice test set into a Myna corpus manifest.

Shows each sentence of bench/voice/script.txt, records it from the default
PipeWire microphone (16 kHz mono, the format the engines use) and writes
manifest.json next to the audio. Recordings stay outside the repository.

    python3 bench/record_voice.py                 # record everything
    python3 bench/record_voice.py --redo tech-03  # re-record one clip

Keys per sentence: Enter starts, Enter stops; then Enter keeps it,
r re-records, s skips, q quits (what is recorded so far is kept).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import wave
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_OUT = Path.home() / ".cache/macaw-bench/voice"


def read_script(path: Path) -> list[tuple[str, str, str]]:
    seen: Counter[str] = Counter()
    lines = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        category, text = raw.split("|", 1)
        seen[category] += 1
        lines.append((f"{category}-{seen[category]:02d}", category, text.strip()))
    return lines


def record(dest: Path, target: str | None) -> float:
    input("   [Enter] start recording ")
    proc = subprocess.Popen(
        ["pw-record", "--rate", "16000", "--channels", "1", "--format", "s16",
         *(["--target", target] if target else []), str(dest)],
        stderr=subprocess.DEVNULL,
    )
    input("   ● recording... [Enter] stop ")
    proc.terminate()
    proc.wait()
    with wave.open(str(dest), "rb") as w:
        return w.getnframes() / w.getframerate()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--script", type=Path, default=HERE / "voice/script.txt")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--target", help="PipeWire source node.name (default: the default microphone)")
    ap.add_argument("--redo", nargs="*", default=None, help="clip ids to re-record")
    args = ap.parse_args()

    audio = args.out / "audio"
    audio.mkdir(parents=True, exist_ok=True)
    manifest_path = args.out / "manifest.json"
    clips = {}
    if manifest_path.exists():
        clips = {c["id"]: c for c in json.loads(manifest_path.read_text())["clips"]}

    script = read_script(args.script)
    todo = [s for s in script if (s[0] in args.redo if args.redo else s[0] not in clips)]
    print(f"{len(todo)} sentences to record ({len(clips)} already done). "
          "Speak as you would dictate; a short pause before and after is fine.\n")

    try:
        for n, (cid, category, text) in enumerate(todo, 1):
            while True:
                print(f"[{n}/{len(todo)}] {cid}\n\n   {text}\n")
                dest = audio / f"{cid}.wav"
                seconds = record(dest, args.target)
                choice = input(f"   {seconds:.1f}s. [Enter] keep, r redo, s skip, q quit: ").strip().lower()
                if choice == "r":
                    continue
                if choice == "s":
                    dest.unlink(missing_ok=True)
                    break
                clips[cid] = {
                    "id": cid, "path": f"audio/{cid}.wav", "text": text, "language": "en",
                    "category": category, "duration_seconds": round(seconds, 3),
                    "sample_rate_hz": 16000, "channels": 1, "source": f"personal:macaw-voice:{args.target or 'default-source'}",
                    "license": "LicenseRef-private",
                    "sha256": hashlib.sha256(dest.read_bytes()).hexdigest(),
                }
                print()
                if choice == "q":
                    raise KeyboardInterrupt
                break
    except KeyboardInterrupt:
        print("\nstopping; progress saved")
    finally:
        order = {s[0]: i for i, s in enumerate(script)}
        manifest = {
            "schema_version": 1,
            "generator": "macaw bench/record_voice.py",
            "clips": sorted(clips.values(), key=lambda c: order.get(c["id"], 1 << 30)),
        }
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
        total = sum(c["duration_seconds"] for c in clips.values())
        print(f"{len(clips)}/{len(script)} clips, {total / 60:.1f} min -> {manifest_path}")


if __name__ == "__main__":
    main()
