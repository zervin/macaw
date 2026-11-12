# Benchmarks

`stt_bench.py` transcribes each clip of a Myna corpus manifest whole (what dictation does
when you stop speaking), times it, and scores it with Myna's own metrics. WER is the
primary normalizer (case and punctuation folded); WERw is Whisper's English normalizer,
as on the Open ASR Leaderboard. `run-vulkan-vs-cpu.sh` runs the comparison below.

## Whisper on the GPU (Vulkan) vs Parakeet on the CPU — 2026-11-11

Machine: Ryzen 7 with Radeon 780M (RADV, Vulkan 1.4, cooperative matrix), 16 threads,
Debian 13. Corpora: 202-clip speaker-balanced subsets of LibriSpeech test-clean
(30.4 min) and test-other (23.3 min), from `myna-bench download-corpus`.

| Engine | Set | WER % | WERw % | Median latency | p95 latency | RTFx |
|---|---|---|---|---|---|---|
| Parakeet TDT 0.6B v3 int8, CPU (Myna) | clean | 2.47 | 2.25 | **0.19 s** | **0.47 s** | **41.6** |
| Whisper large-v3-turbo f16, Vulkan | clean | 2.54 | 1.96 | 0.96 s | 1.15 s | 9.2 |
| Whisper large-v3-turbo q5_0, Vulkan | clean | 2.58 | 1.96 | 0.83 s | 0.94 s | 10.7 |
| Parakeet TDT 0.6B v3 int8, CPU (Myna) | other | 4.17 | 4.01 | **0.14 s** | **0.36 s** | **40.4** |
| Whisper large-v3-turbo f16, Vulkan | other | 4.47 | 3.79 | 0.93 s | 1.12 s | 7.2 |
| Whisper large-v3-turbo q5_0, Vulkan | other | 4.68 | 3.85 | 0.80 s | 0.89 s | 8.6 |

Paired bootstrap (5000 resamples over clips): every Whisper-minus-Parakeet WER and WERw
difference has a 95% interval that includes zero, between −0.8 and +1.4 points.
**Accuracy is tied; Parakeet on the CPU is 4–6× faster.** whisper.cpp v1.9.5, server
defaults (flash attention on, 8 threads), language fixed to English.

Caveats: LibriSpeech is read audiobook speech, close to saturated for both models. It
says little about your own voice, microphone, accent or vocabulary, which is what
dictation quality depends on.

## Personal voice test — 2026-11-11

39 sentences from `voice/script.txt` (4.4 min), read into the Framework 13 laptop mic
after fixing its power-save glitch (see the WirePlumber note in the project memory).
Recordings and transcripts stay local. WERw, Whisper's English normalizer:

| Engine | Overall | Tech | Names | Median latency | Cost |
|---|---|---|---|---|---|
| Parakeet int8, CPU (Myna) | 6.1 % | 15.3 % | 5.6 % | 0.16 s | local |
| Whisper large-v3-turbo, Vulkan | 6.0 % | 8.7 % | 5.6 % | 0.89 s | local |
| Voxtral Mini Transcribe 3 (API) | 6.9 % | 8.0 % | 3.7 % | 0.63 s | $0.0035/min |
| Voxtral Small Transcribe 3 (API) | 6.4 % | 9.3 % | 1.9 % | 0.70 s | $0.004/min |
| Voxtral Mini 3 + `voice/vocabulary.txt` as context_bias | **5.1 %** | **3.3 %** | 1.9 % | 0.65 s | $0.0035/min |

Number-heavy sentences are scored against spelled-out references, so engines that write
digits ("6:45", "555-213-8900") look worse there than they are. Next: the same vocabulary
through Myna's Parakeet keyword boosting.
