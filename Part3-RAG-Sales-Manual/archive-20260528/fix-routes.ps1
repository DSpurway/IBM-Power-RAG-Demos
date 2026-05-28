# Fix Routes Configuration for RAG Demo
# This script creates the frontend route and removes unnecessary backend/granite routes

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Fixing Routes Configuration" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Check current namespace
$NAMESPACE = oc project -q
Write-Host "Current namespace: $NAMESPACE" -ForegroundColor Yellow
Write-Host ""

# Step 1: Create the frontend route
Write-Host "Step 1: Creating carbon-rag-ui route..." -ForegroundColor Green

$routeYaml = @"
apiVersion: route.openshift.io/v1
kind: Route
metadata:
  name: carbon-rag-ui
  namespace: $NAMESPACE
  labels:
    app: carbon-rag-ui
  annotations:
    haproxy.router.openshift.io/timeout: 60s
spec:
  to:
    kind: Service
    name: carbon-rag-ui
  port:
    targetPort: http
  tls:
    termination: edge
    insecureEdgeTerminationPolicy: Redirect
"@

$routeYaml | oc apply -f -

Write-Host ""
Write-Host "Step 2: Removing unnecessary backend route..." -ForegroundColor Green
oc delete route rag-backend --ignore-not-found=true

Write-Host ""
Write-Host "Step 3: Removing unnecessary granite-service route..." -ForegroundColor Green
oc delete route granite-service --ignore-not-found=true

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Routes Configuration Complete" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Display current routes
Write-Host "Current routes in namespace ${NAMESPACE}:" -ForegroundColor Yellow
oc get routes

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Frontend URL" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

$UI_URL = oc get route carbon-rag-ui -o jsonpath='{.spec.host}' 2>$null
if ($UI_URL) {
    Write-Host "Carbon RAG UI: https://$UI_URL" -ForegroundColor Green
} else {
    Write-Host "Warning: carbon-rag-ui route not found" -ForegroundColor Red
}
Write-Host ""

# Made with Bob
