#!/usr/bin/env python3
"""Compare speech recognition engines on a Myna corpus manifest.

Each clip is transcribed whole (what dictation does when you stop speaking),
timed wall-clock, and scored with Myna's own metrics: the primary normalizer
(case and punctuation folded) and Whisper's normalizer (Open ASR Leaderboard).

Run inside Myna's server environment so its testbed modules import:

    uv run --project myna/server python bench/stt_bench.py \\
        --engine parakeet --manifest ~/.cache/macaw-bench/test-clean/manifest.json \\
        --out results/parakeet-cpu-clean.jsonl

    uv run --project myna/server python bench/stt_bench.py \\
        --engine whisper-server --url http://127.0.0.1:8178 \\
        --manifest ... --out results/whisper-turbo-vulkan-clean.jsonl
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import time
import urllib.request
import uuid
import wave
from pathlib import Path

import numpy as np

from myna.testbed.corpus import load_manifest
from myna.testbed.metrics import normalize, whisper_normalizer, word_error_rate


def read_wav(path: Path) -> np.ndarray:
    with wave.open(str(path), "rb") as w:
        if w.getframerate() != 16000 or w.getnchannels() != 1 or w.getsampwidth() != 2:
            raise ValueError(f"{path}: expected 16 kHz mono 16-bit")
        pcm = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
    return pcm.astype(np.float32) / 32768.0


class Parakeet:
    def __init__(self, model_dir: str | None) -> None:
        from myna.testbed.parakeet import ParakeetAdapter, _default_model_dir

        self.adapter = ParakeetAdapter(model_dir or _default_model_dir())
        self.model = asyncio.run(self.adapter._load_model())

    def warm(self, clip) -> None:
        self(clip)

    def __call__(self, clip) -> str:
        words = self.model.transcribe_words(read_wav(clip.path))
        return "".join(w.text for w in words).strip()


class WhisperServer:
    """whisper.cpp's whisper-server, model already loaded."""

    def __init__(self, url: str, language: str) -> None:
        self.url = url.rstrip("/") + "/inference"
        self.language = language

    def warm(self, clip) -> None:
        self(clip)

    def __call__(self, clip) -> str:
        boundary = uuid.uuid4().hex
        fields = {"response_format": "json", "language": self.language, "temperature": "0.0"}
        body = b""
        for k, v in fields.items():
            body += f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
        body += (
            f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="a.wav"\r\n'
            "Content-Type: audio/wav\r\n\r\n"
        ).encode() + clip.path.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
        req = urllib.request.Request(
            self.url, data=body, headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}
        )
        with urllib.request.urlopen(req, timeout=300) as r:
            return json.load(r)["text"].strip()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--engine", choices=["parakeet", "whisper-server"], required=True)
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--model", help="parakeet model dir (default: the staged cache)")
    ap.add_argument("--url", default="http://127.0.0.1:8178")
    ap.add_argument("--language", default="en")
    ap.add_argument("--label", help="free-text label stored on every row")
    ap.add_argument("-n", type=int, default=0, help="only the first N clips")
    args = ap.parse_args()

    clips = load_manifest(args.manifest)
    if args.n:
        clips = clips[: args.n]
    engine = Parakeet(args.model) if args.engine == "parakeet" else WhisperServer(args.url, args.language)
    engine.warm(clips[0])  # model load and first-run kernel compiles are not decode time

    args.out.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    with args.out.open("w") as out:
        for i, clip in enumerate(clips, 1):
            t0 = time.perf_counter()
            hyp = engine(clip)
            dt = time.perf_counter() - t0
            wn = whisper_normalizer(clip.language)
            row = {
                "label": args.label or args.engine,
                "clip": clip.id,
                "audio_s": clip.duration_seconds,
                "decode_s": dt,
                "ref": clip.text,
                "hyp": hyp,
                "wer": word_error_rate(normalize(clip.text), normalize(hyp)).__dict__,
                "wer_w": word_error_rate(wn(clip.text), wn(hyp)).__dict__,
            }
            rows.append(row)
            out.write(json.dumps(row) + "\n")
            if i % 25 == 0:
                print(f"{i}/{len(clips)}", flush=True)

    def pooled(key: str) -> float:
        edits = sum(r[key]["substitutions"] + r[key]["deletions"] + r[key]["insertions"] for r in rows)
        return 100 * edits / sum(r[key]["reference_length"] for r in rows)

    audio = sum(r["audio_s"] for r in rows)
    decode = sum(r["decode_s"] for r in rows)
    lat = sorted(r["decode_s"] for r in rows)
    print(json.dumps({
        "label": args.label or args.engine,
        "clips": len(rows),
        "audio_min": round(audio / 60, 1),
        "WER%": round(pooled("wer"), 2),
        "WERw%": round(pooled("wer_w"), 2),
        "RTFx": round(audio / decode, 1),
        "latency_median_s": round(statistics.median(lat), 3),
        "latency_p95_s": round(lat[int(0.95 * (len(lat) - 1))], 3),
    }))


if __name__ == "__main__":
    main()
