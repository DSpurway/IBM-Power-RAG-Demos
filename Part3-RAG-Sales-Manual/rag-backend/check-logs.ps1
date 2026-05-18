# Quick script to check backend logs
$POD = oc get pods -l app=rag-backend -o jsonpath='{.items[0].metadata.name}' 2>$null

if ($POD) {
    Write-Host "Checking logs for pod: $POD" -ForegroundColor Cyan
    oc logs $POD --tail=100
} else {
    Write-Host "No rag-backend pod found. Checking all pods:" -ForegroundColor Yellow
    oc get pods
}

# Made with Bob
