# Benchmarks

`stt_bench.py` transcribes each clip of a Myna corpus manifest whole (what dictation does
when you stop speaking), times it, and scores it with Myna's own metrics. WER is the
primary normalizer (case and punctuation folded); WERw is Whisper's English normalizer,
as on the Open ASR Leaderboard. `run-vulkan-vs-cpu.sh` runs the comparison below.

## What we learned

1. **The GPU does not buy accuracy or speed for dictation.** Whisper large-v3-turbo on
   a Radeon 780M through Vulkan ties Parakeet int8 on the CPU for accuracy and is 4–6×
   slower per utterance. Vulkan is still a 10× win over Whisper on the CPU, so it matters
   if you want Whisper, but Parakeet on the CPU is the better default.
2. **A cloud model is better at hearing, not at your words.** Mistral's Voxtral beats
   Parakeet on hard common words, but without help it gets technical names wrong too.
3. **A personal vocabulary is the biggest lever.** Myna's keyword boosting with a list of
   the words you actually say cut Parakeet's errors on a jargon-heavy test from 22 % to
   9 %, ahead of the cloud model without a list (11 %), at no cost in privacy and about
   0.1 s of latency, with no false hits on plain speech. A generic tech list barely
   helped (22 → 19 %): it has to be your words. In Myna, set them with
   `gsettings set com.canonical.Myna.Dictation vocabulary "['…', …]"` (up to 100), then
   restart `myna-desktop`; the running daemon did not pick up the change in our test.
4. **Fix the microphone first.** On a Framework 13 AMD the internal mic woke from
   power-save with about 1.5 s of full-scale noise, and mic boost clipped speech; a
   WirePlumber no-suspend rule and boost at 0 fixed both.

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

| Parakeet int8 + `voice/vocabulary.txt` as Myna keywords | 4.8 % | 10.0 % | 3.7 % | 0.22 s | local |

Number-heavy sentences are scored against spelled-out references, so engines that write
digits ("6:45", "555-213-8900") look worse there than they are. Keyword boosting changed
only sentences that contain a listed term.

## Personal vocabulary from your own notes — 2026-11-12

A 99-term list built from the speaker's own notes (tools, products, project and host
names that are not ordinary English, ranked by how many notes use them), and 38 sentences
that use every term at least once, 6 of them plain speech with none. Same laptop mic,
mic boost off. The list, script, audio and transcripts are private and not in this
repository. WERw:

| Engine | Overall | Plain sentences | Terms exact | Median latency |
|---|---|---|---|---|
| Parakeet int8, no list | 22.1 % | 0.0 % | 34 / 99 | 0.15 s |
| Parakeet + the generic 33-term list | 19.2 % | 0.0 % | 45 / 99 | 0.18 s |
| **Parakeet + the personal 99-term list** | **8.7 %** | 0.0 % | 84 / 99 | 0.23 s |
| Voxtral Mini Transcribe 3, no list | 10.7 % | 1.2 % | 66 / 99 | 0.61 s |
| Voxtral Mini 3 + the personal list as context_bias | 3.5 % | 1.2 % | 90 / 99 | 0.61 s |

**A personal list matters more than the model.** Local Parakeet with the user's own list
beats the cloud model without one, and no plain sentence changed. Parakeet's remaining
misses are words far from their spelling (Venafi → "Vinify", Tauri → "Atari", n8n → "NAM",
ONNX → "Onyx") and three biasing artifacts worth reporting upstream: "systemd" becomes
"Systemd D", "Gradle builds" fuses into "GradleBills", and "Cloudflare serves" gains a
stray "s".
