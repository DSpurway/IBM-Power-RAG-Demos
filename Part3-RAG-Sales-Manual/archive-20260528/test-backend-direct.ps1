# Test backend collections endpoint directly from pod
$response = oc exec rag-backend-d489d789-z4hwf -- curl -s http://localhost:8080/api/collections
$data = $response | ConvertFrom-Json

Write-Host "Collections Map: $($data.collections_map.Count) items"
Write-Host "Collections Details: $($data.collections_details.Count) items"
Write-Host "Other Collections: $($data.other_collections.Count) items"
Write-Host "Total Documents: $($data.total_documents)"

Write-Host "`nFirst few collections_map entries:"
$data.collections_map.PSObject.Properties | Select-Object -First 5 | ForEach-Object {
    Write-Host "  $($_.Name) -> $($_.Value)"
}

Write-Host "`nFirst few other_collections:"
$data.other_collections | Select-Object -First 5 | ForEach-Object {
    Write-Host "  $_"
}

# Made with Bob
