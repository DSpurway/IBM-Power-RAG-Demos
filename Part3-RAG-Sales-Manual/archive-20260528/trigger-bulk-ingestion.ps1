#!/usr/bin/env pwsh
# Script to trigger bulk ingestion directly via backend API
# Bypasses UI to avoid browser storage issues

Write-Host "=== IBM Power Sales Manual Bulk Ingestion ===" -ForegroundColor Cyan
Write-Host ""

# Get the RAG backend pod name
Write-Host "Finding RAG backend pod..." -ForegroundColor Yellow
$podName = oc get pods -l app=rag-backend -o jsonpath='{.items[0].metadata.name}'

if (-not $podName) {
    Write-Host "ERROR: Could not find RAG backend pod" -ForegroundColor Red
    exit 1
}

Write-Host "Found pod: $podName" -ForegroundColor Green
Write-Host ""

# Initialize bulk ingestion
Write-Host "Initializing bulk ingestion..." -ForegroundColor Yellow
$initResult = oc exec $podName -- curl -s -X POST http://localhost:8080/api/init-bulk-ingestion -H "Content-Type: application/json" -d '{"total":26}'
Write-Host "Init response: $initResult" -ForegroundColor Gray
Write-Host ""

# Server list in correct order (Power11 -> Power10 -> Power9, largest first)
$servers = @(
    @{model="E1180"; name="IBM Power E1180"; processor="POWER11"},
    @{model="E1150"; name="IBM Power E1150"; processor="POWER11"},
    @{model="S1124"; name="IBM Power S1124"; processor="POWER11"},
    @{model="S1122"; name="IBM Power S1122"; processor="POWER11"},
    @{model="E1080"; name="IBM Power E1080"; processor="POWER10"},
    @{model="E1050"; name="IBM Power E1050"; processor="POWER10"},
    @{model="S1024"; name="IBM Power S1024"; processor="POWER10"},
    @{model="S1022"; name="IBM Power S1022"; processor="POWER10"},
    @{model="S1014"; name="IBM Power S1014"; processor="POWER10"},
    @{model="S1012"; name="IBM Power S1012"; processor="POWER10"},
    @{model="L1024"; name="IBM Power L1024"; processor="POWER10"},
    @{model="L1022"; name="IBM Power L1022"; processor="POWER10"},
    @{model="E980"; name="IBM Power System E980"; processor="POWER9"},
    @{model="E950"; name="IBM Power System E950"; processor="POWER9"},
    @{model="S924"; name="IBM Power System S924"; processor="POWER9"},
    @{model="S924-G"; name="IBM Power System S924"; processor="POWER9"},
    @{model="S922"; name="IBM Power System S922"; processor="POWER9"},
    @{model="S922-G"; name="IBM Power System S922"; processor="POWER9"},
    @{model="S914"; name="IBM Power System S914"; processor="POWER9"},
    @{model="S914-G"; name="IBM Power System S914"; processor="POWER9"},
    @{model="H924"; name="IBM Power System H924"; processor="POWER9"},
    @{model="H922"; name="IBM Power System H922"; processor="POWER9"},
    @{model="IC922"; name="IBM Power System IC922"; processor="POWER9"},
    @{model="L922"; name="IBM Power System L922"; processor="POWER9"},
    @{model="LC922"; name="IBM Power System LC922"; processor="POWER9"},
    @{model="LC921"; name="IBM Power System LC921"; processor="POWER9"}
)

$completed = 0
$failed = 0

Write-Host "Starting ingestion of $($servers.Count) servers..." -ForegroundColor Cyan
Write-Host "This will take several hours. Press Ctrl+C to stop." -ForegroundColor Yellow
Write-Host ""

foreach ($server in $servers) {
    $current = $completed + $failed + 1
    Write-Host "[$current/$($servers.Count)] Processing $($server.model) ($($server.name))..." -ForegroundColor Cyan
    
    # Create JSON payload
    $payload = @{
        server_model = $server.model
        server_name = $server.name
        processor = $server.processor
    } | ConvertTo-Json -Compress
    
    # Escape quotes for shell
    $payload = $payload.Replace('"', '\"')
    
    try {
        # Call backend API
        $result = oc exec $podName -- curl -s -X POST http://localhost:8080/api/ingest-sales-manual -H "Content-Type: application/json" -d "$payload" --max-time 600
        
        if ($result -match '"success":\s*true') {
            $completed++
            Write-Host "  ✓ Success" -ForegroundColor Green
        } else {
            $failed++
            Write-Host "  ✗ Failed: $result" -ForegroundColor Red
        }
    } catch {
        $failed++
        Write-Host "  ✗ Error: $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

Write-Host "=== Bulk Ingestion Complete ===" -ForegroundColor Cyan
Write-Host "Completed: $completed" -ForegroundColor Green
Write-Host "Failed: $failed" -ForegroundColor $(if ($failed -gt 0) { "Red" } else { "Green" })
Write-Host ""
Write-Host "Check OpenSearch indices:" -ForegroundColor Yellow
Write-Host "  oc exec $podName -- curl -s http://opensearch-service:9200/_cat/indices?v" -ForegroundColor Gray

# Made with Bob
