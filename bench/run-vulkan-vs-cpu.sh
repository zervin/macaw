#!/usr/bin/env bash
# Whisper large-v3-turbo (f16 and q5_0) on the GPU via whisper.cpp Vulkan,
# versus Myna's Parakeet int8 on the CPU, on LibriSpeech test-clean and
# test-other subsets. Runs one engine at a time. Results: bench/results/.
set -euo pipefail

here="$(cd "$(dirname "$0")/.." && pwd)"
bench=${MACAW_BENCH:-$HOME/.cache/macaw-bench}
out="$here/bench/results"
mkdir -p "$out"
export LD_LIBRARY_PATH="$bench/whisper.cpp/build/bin"

run() { # engine label set [extra args]
    local engine=$1 label=$2 set=$3; shift 3
    uv run --project "$here/myna/server" python "$here/bench/stt_bench.py" \
        --engine "$engine" --label "$label-$set" \
        --manifest "$bench/test-$set/manifest.json" \
        --out "$out/$label-$set.jsonl" "$@" | tail -1 | tee -a "$out/summary.jsonl"
}

if curl -s -o /dev/null http://127.0.0.1:8178/; then
    echo "something already listens on 127.0.0.1:8178; stop it first" >&2
    exit 1
fi
for model in large-v3-turbo large-v3-turbo-q5_0; do
    "$bench/whisper.cpp/build/bin/whisper-server" -m "$bench/models/ggml-$model.bin" \
        --host 127.0.0.1 --port 8178 -t 8 -l en > "$out/whisper-server-$model.log" 2>&1 &
    pid=$!
    until curl -s -o /dev/null http://127.0.0.1:8178/; do sleep 1; done
    for set in clean other; do run whisper-server "whisper-$model-vulkan" $set; done
    kill $pid; wait $pid 2>/dev/null || true
done

for set in clean other; do run parakeet parakeet-int8-cpu $set; done
