# Test if UI pod can reach backend and get correct response
Write-Host "Testing UI pod calling backend service..."
$response = oc exec carbon-rag-ui-5db4fc774c-4lwp5 -- curl -s http://rag-backend:8080/api/collections
$data = $response | ConvertFrom-Json

Write-Host "`nResponse from backend (via service):"
Write-Host "  collections_map: $($data.collections_map.Count) items"
Write-Host "  collections_details: $($data.collections_details.Count) items"
Write-Host "  other_collections: $($data.other_collections.Count) items"
Write-Host "  total_documents: $($data.total_documents)"

if ($data.collections_map.Count -gt 0) {
    Write-Host "`n✓ SUCCESS: Backend is returning MTM mappings!"
    Write-Host "`nFirst 5 MTMs:"
    $data.collections_map.PSObject.Properties | Select-Object -First 5 | ForEach-Object {
        Write-Host "  $($_.Name) -> $($_.Value)"
    }
} else {
    Write-Host "`n✗ PROBLEM: Backend returning empty collections_map"
    Write-Host "UI is hitting a different backend or there is a caching issue"
}

# Made with Bob
