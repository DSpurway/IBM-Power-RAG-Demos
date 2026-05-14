# Test script for activation feature queries
# Tests the new activation lookup functionality

param(
    [string]$BackendUrl = "http://localhost:8080",
    [string]$Collection = "ibm_power_s1022"
)

# Ensure URL has https:// prefix
if ($BackendUrl -notmatch "^https?://") {
    $BackendUrl = "https://$BackendUrl"
}

# Skip SSL certificate validation for self-signed certs
add-type @"
    using System.Net;
    using System.Security.Cryptography.X509Certificates;
    public class TrustAllCertsPolicy : ICertificatePolicy {
        public bool CheckValidationResult(
            ServicePoint srvPoint, X509Certificate certificate,
            WebRequest request, int certificateProblem) {
            return true;
        }
    }
"@
[System.Net.ServicePointManager]::CertificatePolicy = New-Object TrustAllCertsPolicy
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.SecurityProtocolType]::Tls12

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Activation Feature Query Test" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Backend URL: $BackendUrl" -ForegroundColor Yellow
Write-Host "Collection: $Collection" -ForegroundColor Yellow
Write-Host ""

# Test queries
$queries = @(
    "What processor activations are available for this server?",
    "Can I still buy memory activations?",
    "List all activation features",
    "Are there any processor activation features still available?",
    "Show me memory activation options"
)

foreach ($query in $queries) {
    Write-Host "----------------------------------------" -ForegroundColor Gray
    Write-Host "Query: $query" -ForegroundColor Green
    Write-Host ""
    
    $body = @{
        question = $query
        collection_name = $Collection
        k = 10
    } | ConvertTo-Json
    
    try {
        $response = Invoke-RestMethod -Uri "$BackendUrl/api/search" -Method Post -Body $body -ContentType "application/json"
        
        Write-Host "Query Type: $($response.query_type)" -ForegroundColor Cyan
        
        if ($response.query_type -eq "activation_lookup") {
            Write-Host "Correctly classified as activation lookup" -ForegroundColor Green
            Write-Host ""
            
            if ($response.success) {
                Write-Host "Summary:" -ForegroundColor Yellow
                Write-Host "  Total Features: $($response.summary.total)" -ForegroundColor White
                Write-Host "  Available: $($response.summary.available)" -ForegroundColor Green
                Write-Host "  Discontinued: $($response.summary.discontinued)" -ForegroundColor Red
                Write-Host ""
                
                if ($response.features -and $response.features.Count -gt 0) {
                    Write-Host "Features Found:" -ForegroundColor Yellow
                    foreach ($feature in $response.features) {
                        if ($feature.is_available) {
                            $status = "Available"
                            $color = "Green"
                        } else {
                            $status = $feature.status
                            $color = "Red"
                        }
                        Write-Host "  $($feature.feature_code): $($feature.description)" -ForegroundColor White
                        Write-Host "    Status: $status" -ForegroundColor $color
                    }
                }
                
                Write-Host ""
                Write-Host "Answer:" -ForegroundColor Yellow
                Write-Host $response.answer -ForegroundColor White
            } else {
                Write-Host "Query failed: $($response.error)" -ForegroundColor Red
            }
        } else {
            Write-Host "Not classified as activation lookup (got: $($response.query_type))" -ForegroundColor Yellow
        }
        
    } catch {
        Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    }
    
    Write-Host ""
    Start-Sleep -Seconds 1
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Test Complete" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Made with Bob
