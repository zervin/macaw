#!/usr/bin/env python3
"""Check a microphone's levels before recording a test set.

Records 10 s of raw stereo at 48 kHz: stay quiet for the first 3 s (noise
floor), then read a sentence at dictation volume. Reports peak, clipping,
speech level, noise floor, signal-to-noise and left/right correlation (a
negative correlation means one channel is phase-inverted, so a mono downmix
cancels speech).

    uv run --project myna/server python bench/mic_check.py [--target <node.name>]
"""

import argparse
import subprocess
import sys
import tempfile
import time
import wave

import numpy as np


def db(x: float) -> float:
    return 20 * np.log10(max(x, 1e-9))


ap = argparse.ArgumentParser()
ap.add_argument("--target")
args = ap.parse_args()

input("Press Enter, then stay quiet for 3 s until the sentence appears. ")
with tempfile.NamedTemporaryFile(suffix=".wav") as f:
    cmd = ["pw-record", "--rate", "48000", "--channels", "2", "--format", "s16",
           *(["--target", args.target] if args.target else []), f.name]
    proc = subprocess.Popen(cmd, stderr=subprocess.DEVNULL)
    print("Recording. Stay QUIET...", flush=True)
    time.sleep(3)
    print("Now read at normal dictation volume:\n\n"
          "   The quick brown fox jumps over the lazy dog, and then I check my email.\n", flush=True)
    time.sleep(7)
    proc.terminate()
    proc.wait()
    with wave.open(f.name) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).reshape(-1, 2) / 32768.0

rate = 48000
quiet, speech = x[int(0.5 * rate):int(2.5 * rate)], x[int(3.5 * rate):]
mono = speech.mean(axis=1)


def rms(a):
    return float(np.sqrt(np.mean(a ** 2)))


# Speech level: RMS over the loudest 30% of 50 ms frames, so pauses don't drag it down.
frames = mono[: len(mono) // 2400 * 2400].reshape(-1, 2400)
loud = np.sort(np.sqrt((frames ** 2).mean(axis=1)))[-max(1, len(frames) * 3 // 10):]
speech_db, noise_db = db(float(np.mean(loud))), db(rms(quiet.mean(axis=1)))
peak = float(np.abs(x).max())
clipped = float(np.mean(np.abs(x) > 0.99)) * 100
corr = float(np.corrcoef(speech[:, 0], speech[:, 1])[0, 1])
l_db, r_db = db(rms(speech[:, 0])), db(rms(speech[:, 1]))

print(f"peak            {db(peak):6.1f} dBFS   (clipped samples {clipped:.3f}%)")
print(f"speech level    {speech_db:6.1f} dBFS   (aim for about -30 to -15)")
print(f"noise floor     {noise_db:6.1f} dBFS")
print(f"SNR             {speech_db - noise_db:6.1f} dB     (above 30 is good, under 20 hurts)")
print(f"left / right    {l_db:6.1f} / {r_db:.1f} dBFS")
print(f"L/R correlation {corr:6.2f}        (near +1 normal; negative = phase-inverted pair)")
sys.exit(0)
