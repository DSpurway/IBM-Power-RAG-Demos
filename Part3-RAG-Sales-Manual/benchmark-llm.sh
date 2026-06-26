#!/bin/bash
# =============================================================================
# LLM Performance Benchmark: llama.cpp (granite-service) vs vLLM (vllm-service)
#
# Runs from inside the rag-backend pod — no jq required, uses python3 for JSON.
#
# Usage (from your laptop):
#   POD=$(oc get pod -l app=rag-backend -o jsonpath='{.items[0].metadata.name}')
#   oc exec $POD -- bash -c "curl -sL https://raw.githubusercontent.com/DSpurway/IBM-Power-RAG-Demos/main/Part3-RAG-Sales-Manual/benchmark-llm.sh | bash"
# =============================================================================

set -e

LLAMACPP_HOST="granite-service"
LLAMACPP_PORT="8080"
VLLM_HOST="vllm-service"
VLLM_PORT="8000"
RUNS=3

SHORT_PROMPT="What are the processor options available for the IBM Power S1022 server? Answer concisely."

LONG_PROMPT="Based on the following context about IBM Power servers, answer the question.

Context: The IBM Power S1022 is a 2-socket scale-out server supporting Power10 processors. It supports up to 16 DDIMMs of memory with a maximum of 4TB. The server can be configured with either air cooling or water cooling. It supports PCIe Gen5 slots and has options for both SAS and NVMe storage. The S1022 is designed for enterprise workloads including AI inference, database, and virtualization use cases.

Question: Compare the memory and storage options of the IBM Power S1022, and explain which configuration would be best suited for an AI inference workload that requires fast data access and large model storage.

Provide a detailed technical answer."

# JSON parsing via python3 (always present in the rag-backend image)
json_get() {
    python3 -c "import sys,json; d=json.load(sys.stdin); print(d$1)" 2>/dev/null || echo "N/A"
}

# Escape a string for JSON using python3
json_escape() {
    python3 -c "import sys,json; print(json.dumps(sys.stdin.read()))" <<< "$1"
}

run_llamacpp() {
    local prompt="$1"
    local escaped start end elapsed result content tps

    escaped=$(json_escape "$prompt")
    start=$(date +%s%N)
    result=$(curl -s --max-time 300 \
        -X POST "http://${LLAMACPP_HOST}:${LLAMACPP_PORT}/completion" \
        -H "Content-Type: application/json" \
        -d "{\"prompt\": ${escaped}, \"n_predict\": 256, \"temperature\": 0.1, \"stream\": false}")
    end=$(date +%s%N)

    elapsed=$(( (end - start) / 1000000 ))
    content=$(echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('content','ERROR'))" 2>/dev/null || echo "ERROR")
    tps=$(echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(round(d.get('timings',{}).get('predicted_per_second',0),1))" 2>/dev/null || echo "N/A")

    echo "${elapsed}|${tps}|${content}"
}

run_vllm() {
    local prompt="$1"
    local escaped start end elapsed result content tps completion_tokens

    escaped=$(json_escape "$prompt")
    start=$(date +%s%N)
    result=$(curl -s --max-time 300 \
        -X POST "http://${VLLM_HOST}:${VLLM_PORT}/v1/chat/completions" \
        -H "Content-Type: application/json" \
        -d "{\"model\": \"granite\", \"messages\": [{\"role\": \"user\", \"content\": ${escaped}}], \"max_tokens\": 256, \"temperature\": 0.1, \"stream\": false}")
    end=$(date +%s%N)

    elapsed=$(( (end - start) / 1000000 ))
    content=$(echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['choices'][0]['message']['content'])" 2>/dev/null || echo "ERROR")
    completion_tokens=$(echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('usage',{}).get('completion_tokens',0))" 2>/dev/null || echo "0")
    if [ "$completion_tokens" -gt 0 ] 2>/dev/null; then
        tps=$(python3 -c "print(round($completion_tokens * 1000 / $elapsed, 1))" 2>/dev/null || echo "N/A")
    else
        tps="N/A"
    fi

    echo "${elapsed}|${tps}|${content}"
}

benchmark_prompt() {
    local label="$1"
    local prompt="$2"

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  Prompt: ${label}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    local llamacpp_total=0 vllm_total=0
    local llamacpp_tps_last="N/A" vllm_tps_last="N/A"
    local llamacpp_answer="" vllm_answer=""

    for i in $(seq 1 $RUNS); do
        echo -n "  Run ${i}/${RUNS} — llama.cpp ... "
        IFS='|' read -r elapsed tps content <<< "$(run_llamacpp "$prompt")"
        llamacpp_total=$((llamacpp_total + elapsed))
        llamacpp_tps_last="$tps"
        llamacpp_answer="$content"
        echo "${elapsed}ms  (${tps} tok/s)"

        echo -n "  Run ${i}/${RUNS} — vLLM      ... "
        IFS='|' read -r elapsed tps content <<< "$(run_vllm "$prompt")"
        vllm_total=$((vllm_total + elapsed))
        vllm_tps_last="$tps"
        vllm_answer="$content"
        echo "${elapsed}ms  (${tps} tok/s)"
    done

    local llamacpp_avg=$((llamacpp_total / RUNS))
    local vllm_avg=$((vllm_total / RUNS))

    echo ""
    echo "  ┌────────────────────┬──────────────┬──────────────┬──────────────┐"
    echo "  │  Engine            │  Avg time    │  Tok/s       │  Format      │"
    echo "  ├────────────────────┼──────────────┼──────────────┼──────────────┤"
    printf "  │  llama.cpp         │  %-12s│  %-12s│  Q4_K_M      │\n" "${llamacpp_avg}ms" "${llamacpp_tps_last}"
    printf "  │  vLLM              │  %-12s│  %-12s│  float32     │\n" "${vllm_avg}ms" "${vllm_tps_last}"
    echo "  └────────────────────┴──────────────┴──────────────┴──────────────┘"

    if [ "$llamacpp_avg" -lt "$vllm_avg" ]; then
        speedup=$(python3 -c "print(round($vllm_avg / $llamacpp_avg, 1))" 2>/dev/null || echo "?")
        echo "  ➜  llama.cpp was ${speedup}x faster on this prompt"
    else
        speedup=$(python3 -c "print(round($llamacpp_avg / $vllm_avg, 1))" 2>/dev/null || echo "?")
        echo "  ➜  vLLM was ${speedup}x faster on this prompt"
    fi

    echo ""
    echo "  --- llama.cpp answer ---"
    echo "$llamacpp_answer" | python3 -c "import sys,textwrap; print('\n'.join('  '+l for l in textwrap.wrap(sys.stdin.read(),72)))" 2>/dev/null || echo "  $llamacpp_answer"
    echo ""
    echo "  --- vLLM answer ---"
    echo "$vllm_answer" | python3 -c "import sys,textwrap; print('\n'.join('  '+l for l in textwrap.wrap(sys.stdin.read(),72)))" 2>/dev/null || echo "  $vllm_answer"
}

# Pre-flight
echo ""
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║   IBM Power RAG Demo — LLM Benchmark: llama.cpp vs vLLM             ║"
echo "║   Model: Granite 3.3 2B Instruct  |  Q4_K_M vs float32             ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""
echo "Checking service availability..."

if curl -s --max-time 5 "http://${LLAMACPP_HOST}:${LLAMACPP_PORT}/health" > /dev/null 2>&1; then
    LLAMACPP_OK="ok"
else
    LLAMACPP_OK="unreachable"
fi
if curl -s --max-time 5 "http://${VLLM_HOST}:${VLLM_PORT}/health" > /dev/null 2>&1; then
    VLLM_OK="ok"
else
    VLLM_OK="unreachable"
fi

echo "  llama.cpp (granite-service:8080): ${LLAMACPP_OK}"
echo "  vLLM      (vllm-service:8000):    ${VLLM_OK}"

if [ "$LLAMACPP_OK" = "unreachable" ] || [ "$VLLM_OK" = "unreachable" ]; then
    echo ""
    echo "ERROR: One or both services unreachable."
    exit 1
fi

echo "  Both services ready. Running ${RUNS} iterations per prompt..."

benchmark_prompt "SHORT — Single factual question" "$SHORT_PROMPT"
benchmark_prompt "LONG  — RAG-style contextual query" "$LONG_PROMPT"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Benchmark complete."
echo "  CPU limit: 4 cores each  |  llama.cpp Q4_K_M (1.55GB)  |  vLLM float32 (~10GB)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Made with Bob
