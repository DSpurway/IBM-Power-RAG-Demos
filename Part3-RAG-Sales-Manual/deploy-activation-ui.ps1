# Deploy Activation Features UI Improvements
# This script commits changes and deploys both backend and frontend

Write-Host "=== Activation Features UI Deployment ===" -ForegroundColor Cyan
Write-Host ""

# Step 1: Git operations
Write-Host "Step 1: Committing changes to Git..." -ForegroundColor Yellow
Set-Location -Path "C:\Users\029878866\EMEA-AI-SQUAD\RAG-with-Notebook"

# Stage the files
Write-Host "Staging files..." -ForegroundColor Gray
git add Part3-RAG-Sales-Manual/carbon-rag-ui/src/components/ActivationFeaturesView/ActivationFeaturesView.js
git add Part3-RAG-Sales-Manual/carbon-rag-ui/src/app/api/rag/generate/route.js
git add Part3-RAG-Sales-Manual/carbon-rag-ui/openshift-deployment.yaml
git add Part3-RAG-Sales-Manual/ACTIVATION_UI_IMPROVEMENTS.md

# Show status
Write-Host ""
Write-Host "Git status:" -ForegroundColor Gray
git status --short

# Commit
Write-Host ""
Write-Host "Committing..." -ForegroundColor Gray
git commit -m "Add activation features list+detail view with timeout fixes"

# Push
Write-Host ""
Write-Host "Pushing to GitHub..." -ForegroundColor Gray
git push

Write-Host ""
Write-Host "✓ Git operations complete" -ForegroundColor Green
Write-Host ""

# Step 2: Deploy Frontend
Write-Host "Step 2: Deploying Frontend..." -ForegroundColor Yellow
Set-Location -Path "C:\Users\029878866\EMEA-AI-SQUAD\RAG-with-Notebook\Part3-RAG-Sales-Manual\carbon-rag-ui"

Write-Host "Starting build..." -ForegroundColor Gray
oc start-build carbon-rag-ui --follow

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "Restarting deployment..." -ForegroundColor Gray
    oc rollout restart deployment/carbon-rag-ui
    
    Write-Host ""
    Write-Host "Waiting for rollout..." -ForegroundColor Gray
    oc rollout status deployment/carbon-rag-ui
    
    Write-Host ""
    Write-Host "✓ Frontend deployed successfully" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "✗ Frontend build failed" -ForegroundColor Red
    exit 1
}

# Step 3: Update Route timeout
Write-Host ""
Write-Host "Step 3: Updating Route timeout..." -ForegroundColor Yellow
Write-Host "Applying route configuration..." -ForegroundColor Gray
oc apply -f openshift-deployment.yaml

Write-Host ""
Write-Host "✓ Route timeout updated to 60s" -ForegroundColor Green

# Step 4: Verify deployment
Write-Host ""
Write-Host "Step 4: Verifying deployment..." -ForegroundColor Yellow

Write-Host ""
Write-Host "Frontend pods:" -ForegroundColor Gray
oc get pods | Select-String "carbon-rag-ui"

Write-Host ""
Write-Host "Route details:" -ForegroundColor Gray
oc get route carbon-rag-ui -o jsonpath='{.metadata.annotations.haproxy\.router\.openshift\.io/timeout}'
Write-Host " (timeout)"

Write-Host ""
Write-Host "=== Deployment Complete ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Test with query: 'S1022 activations'" -ForegroundColor White
Write-Host "2. Click on features in the left panel" -ForegroundColor White
Write-Host "3. Verify chunk_text displays in right panel" -ForegroundColor White
Write-Host "4. Compare LLM descriptions with source content" -ForegroundColor White
Write-Host ""
Write-Host "If you still see timeouts, check:" -ForegroundColor Yellow
Write-Host "- Backend logs: oc logs -f deployment/rag-backend" -ForegroundColor White
Write-Host "- Frontend logs: oc logs -f deployment/carbon-rag-ui" -ForegroundColor White
Write-Host ""

# Made with Bob
