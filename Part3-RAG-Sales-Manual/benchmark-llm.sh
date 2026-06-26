#!/bin/bash
# =============================================================================
# LLM Performance Benchmark: llama.cpp (granite-service) vs vLLM (vllm-service)
#
# Tests both services with identical RAG-style prompts and reports:
#   - Total response time (wall clock)
#   - Tokens generated
#   - Tokens per second (where available)
#   - Answer quality (printed for manual review)
#
# Usage:
#   chmod +x benchmark-llm.sh
#   ./benchmark-llm.sh
#
# Requires: oc CLI logged in, jq installed on the test pod
# =============================================================================

set -e

LLAMACPP_HOST="granite-service"
LLAMACPP_PORT="8080"
VLLM_HOST="vllm-service"
VLLM_PORT="8000"
RUNS=3   # Number of times to run each prompt for averaging

# -----------------------------------------------------------------------------
# Test prompts — representative RAG-style queries used in the demo
# Short prompt: quick factual question
# Long prompt:  complex comparison with context (simulates real RAG usage)
# -----------------------------------------------------------------------------

SHORT_PROMPT="What are the processor options available for the IBM Power S1022 server? Answer concisely."

LONG_PROMPT="Based on the following context about IBM Power servers, answer the question.

Context: The IBM Power S1022 is a 2-socket scale-out server supporting Power10 processors. It supports up to 16 DDIMMs of memory with a maximum of 4TB. The server can be configured with either air cooling or water cooling. It supports PCIe Gen5 slots and has options for both SAS and NVMe storage. The S1022 is designed for enterprise workloads including AI inference, database, and virtualization use cases.

Question: Compare the memory and storage options of the IBM Power S1022, and explain which configuration would be best suited for an AI inference workload that requires fast data access and large model storage.

Provide a detailed technical answer."

# -----------------------------------------------------------------------------
# Helper: run a single llamacpp inference and return elapsed seconds + content
# -----------------------------------------------------------------------------
run_llamacpp() {
    local prompt="$1"
    local start end elapsed result content tokens_per_sec

    start=$(date +%s%N)
    result=$(curl -s --max-time 300 \
        -X POST "http://${LLAMACPP_HOST}:${LLAMACPP_PORT}/completion" \
        -H "Content-Type: application/json" \
        -d "{
            \"prompt\": $(echo "$prompt" | jq -Rs .),
            \"n_predict\": 256,
            \"temperature\": 0.1,
            \"stream\": false
        }")
    end=$(date +%s%N)

    elapsed=$(( (end - start) / 1000000 ))  # milliseconds
    content=$(echo "$result" | jq -r '.content // "ERROR: no content"')
    tokens_per_sec=$(echo "$result" | jq -r '.timings.predicted_per_second // "N/A"')

    echo "${elapsed}|${tokens_per_sec}|${content}"
}

# -----------------------------------------------------------------------------
# Helper: run a single vLLM inference and return elapsed seconds + content
# -----------------------------------------------------------------------------
run_vllm() {
    local prompt="$1"
    local start end elapsed result content

    start=$(date +%s%N)
    result=$(curl -s --max-time 300 \
        -X POST "http://${VLLM_HOST}:${VLLM_PORT}/v1/chat/completions" \
        -H "Content-Type: application/json" \
        -d "{
            \"model\": \"granite\",
            \"messages\": [{\"role\": \"user\", \"content\": $(echo "$prompt" | jq -Rs .)}],
            \"max_tokens\": 256,
            \"temperature\": 0.1,
            \"stream\": false
        }")
    end=$(date +%s%N)

    elapsed=$(( (end - start) / 1000000 ))  # milliseconds
    content=$(echo "$result" | jq -r '.choices[0].message.content // "ERROR: no content"')
    # vLLM returns token counts in usage - calculate approx tok/s
    completion_tokens=$(echo "$result" | jq -r '.usage.completion_tokens // 0')
    if [ "$completion_tokens" -gt 0 ] 2>/dev/null; then
        tokens_per_sec=$(echo "scale=1; $completion_tokens * 1000 / $elapsed" | bc 2>/dev/null || echo "N/A")
    else
        tokens_per_sec="N/A"
    fi

    echo "${elapsed}|${tokens_per_sec}|${content}"
}

# -----------------------------------------------------------------------------
# Benchmark a prompt against both services, RUNS times each
# -----------------------------------------------------------------------------
benchmark_prompt() {
    local label="$1"
    local prompt="$2"

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  Prompt: ${label}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    local llamacpp_total=0
    local vllm_total=0
    local llamacpp_tps_last="N/A"
    local vllm_tps_last="N/A"
    local llamacpp_answer=""
    local vllm_answer=""

    for i in $(seq 1 $RUNS); do
        echo -n "  Run ${i}/${RUNS} — llama.cpp ... "
        IFS='|' read -r elapsed tps content <<< "$(run_llamacpp "$prompt")"
        llamacpp_total=$((llamacpp_total + elapsed))
        llamacpp_tps_last="$tps"
        llamacpp_answer="$content"
        echo "${elapsed}ms (${tps} tok/s)"

        echo -n "  Run ${i}/${RUNS} — vLLM      ... "
        IFS='|' read -r elapsed tps content <<< "$(run_vllm "$prompt")"
        vllm_total=$((vllm_total + elapsed))
        vllm_tps_last="$tps"
        vllm_answer="$content"
        echo "${elapsed}ms (${tps} tok/s)"
    done

    local llamacpp_avg=$((llamacpp_total / RUNS))
    local vllm_avg=$((vllm_total / RUNS))

    echo ""
    echo "  ┌─────────────────────────────────────────────────────────────┐"
    echo "  │  Results (${RUNS}-run average)                                     │"
    echo "  ├────────────────────┬──────────────┬──────────────┬──────────┤"
    echo "  │  Engine            │  Avg ms      │  Tok/s       │  Model   │"
    echo "  ├────────────────────┼──────────────┼──────────────┼──────────┤"
    printf "  │  llama.cpp         │  %-12s│  %-12s│  Q4_K_M  │\n" "${llamacpp_avg}ms" "${llamacpp_tps_last}"
    printf "  │  vLLM              │  %-12s│  %-12s│  float32 │\n" "${vllm_avg}ms" "${vllm_tps_last}"
    echo "  └────────────────────┴──────────────┴──────────────┴──────────┘"

    if [ "$llamacpp_avg" -lt "$vllm_avg" ]; then
        speedup=$(echo "scale=1; $vllm_avg / $llamacpp_avg" | bc 2>/dev/null || echo "?")
        echo "  ➜  llama.cpp was ${speedup}× faster on this prompt"
    else
        speedup=$(echo "scale=1; $llamacpp_avg / $vllm_avg" | bc 2>/dev/null || echo "?")
        echo "  ➜  vLLM was ${speedup}× faster on this prompt"
    fi

    echo ""
    echo "  --- llama.cpp answer ---"
    echo "$llamacpp_answer" | fold -s -w 72 | sed 's/^/  /'
    echo ""
    echo "  --- vLLM answer ---"
    echo "$vllm_answer" | fold -s -w 72 | sed 's/^/  /'
}

# -----------------------------------------------------------------------------
# Pre-flight checks
# -----------------------------------------------------------------------------
echo ""
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║   IBM Power RAG Demo — LLM Benchmark: llama.cpp vs vLLM             ║"
echo "║   Model: Granite 3.3 2B Instruct (Q4_K_M vs float32)                ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""
echo "Checking service availability..."

LLAMACPP_OK=$(curl -s --max-time 5 "http://${LLAMACPP_HOST}:${LLAMACPP_PORT}/health" | jq -r '.status // "ok"' 2>/dev/null || echo "unreachable")
VLLM_OK=$(curl -s --max-time 5 "http://${VLLM_HOST}:${VLLM_PORT}/health" 2>/dev/null && echo "ok" || echo "unreachable")

echo "  llama.cpp (granite-service:8080): ${LLAMACPP_OK}"
echo "  vLLM      (vllm-service:8000):    ${VLLM_OK}"

if [ "$LLAMACPP_OK" = "unreachable" ] || [ "$VLLM_OK" = "unreachable" ]; then
    echo ""
    echo "ERROR: One or both services are not reachable. Check pod status:"
    echo "  oc get pods -l 'app in (granite-service,vllm-service)'"
    exit 1
fi

echo ""
echo "  Both services reachable. Starting benchmark (${RUNS} runs per prompt)..."
echo "  Node: $(hostname) | $(nproc) vCPUs available to pod"

# -----------------------------------------------------------------------------
# Run benchmarks
# -----------------------------------------------------------------------------
benchmark_prompt "SHORT — Single factual question" "$SHORT_PROMPT"
benchmark_prompt "LONG  — RAG-style contextual query" "$LONG_PROMPT"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Benchmark complete."
echo "  Note: First run of each may be slower due to KV cache cold start."
echo "  Both services have CPU limit=4 cores, request=2 cores."
echo "  llama.cpp: Granite 3.3 2B Q4_K_M GGUF (1.55 GB)"
echo "  vLLM:      Granite 3.3 2B Instruct float32 safetensors (~10 GB)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Made with Bob
