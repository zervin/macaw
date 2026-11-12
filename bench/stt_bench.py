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
    def __init__(self, model_dir: str | None, keywords: list[str]) -> None:
        from myna.testbed.parakeet import ParakeetAdapter, _default_model_dir

        self.adapter = ParakeetAdapter(model_dir or _default_model_dir())
        self.model = asyncio.run(self.adapter._load_model())
        # The same bias the server builds from a session's `keywords`.
        self.bias = self.model.keyword_bias(tuple(keywords)) if keywords else None

    def warm(self, clip) -> None:
        self(clip)

    def __call__(self, clip) -> str:
        words = self.model.transcribe_words(read_wav(clip.path), self.bias)
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


class MistralApi:
    """Mistral's /v1/audio/transcriptions. Reads MISTRAL_API_KEY from the
    environment; audio is uploaded to Mistral."""

    def __init__(self, model: str, language: str, bias: list[str]) -> None:
        import os

        self.key = os.environ["MISTRAL_API_KEY"]
        self.model, self.language, self.bias = model, language, bias
        self.audio_seconds = 0.0

    def warm(self, clip) -> None:
        pass  # a warm-up call would be billed and is not representative of a first request

    def __call__(self, clip) -> str:
        boundary = uuid.uuid4().hex
        fields = [("model", self.model), ("language", self.language)]
        fields += [("context_bias", b) for b in self.bias]
        body = b"".join(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
            for k, v in fields
        )
        body += (
            f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{clip.path.name}"\r\n'
            "Content-Type: audio/wav\r\n\r\n"
        ).encode() + clip.path.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
        req = urllib.request.Request(
            "https://api.mistral.ai/v1/audio/transcriptions", data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}",
                     "Authorization": f"Bearer {self.key}"},
        )
        with urllib.request.urlopen(req, timeout=120) as r:
            out = json.load(r)
        self.audio_seconds += float((out.get("usage") or {}).get("prompt_audio_seconds") or 0)
        return out["text"].strip()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--engine", choices=["parakeet", "whisper-server", "mistral"], required=True)
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--model", help="parakeet model dir (default: the staged cache)")
    ap.add_argument("--url", default="http://127.0.0.1:8178")
    ap.add_argument("--language", default="en")
    ap.add_argument("--mistral-model", default="voxtral-mini-transcribe-3")
    ap.add_argument("--bias-file", type=Path, help="vocabulary, one term per line: Parakeet keyword bias or Mistral context_bias")
    ap.add_argument("--label", help="free-text label stored on every row")
    ap.add_argument("-n", type=int, default=0, help="only the first N clips")
    args = ap.parse_args()

    clips = load_manifest(args.manifest)
    if args.n:
        clips = clips[: args.n]
    vocab = [t.strip() for t in args.bias_file.read_text().splitlines() if t.strip()] if args.bias_file else []
    if args.engine == "parakeet":
        engine = Parakeet(args.model, vocab)
    elif args.engine == "whisper-server":
        engine = WhisperServer(args.url, args.language)
    else:
        engine = MistralApi(args.mistral_model, args.language, vocab)
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
    billed = getattr(engine, "audio_seconds", 0.0)
    print(json.dumps({
        **({"billed_audio_min": round(billed / 60, 2)} if billed else {}),
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
