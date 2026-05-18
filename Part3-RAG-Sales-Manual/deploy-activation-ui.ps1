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
git add Part3-RAG-Sales-Manual/carbon-rag-ui/src/app/sales-manual/page.js
git add Part3-RAG-Sales-Manual/carbon-rag-ui/src/app/api/rag/generate/route.js
git add Part3-RAG-Sales-Manual/carbon-rag-ui/openshift-deployment.yaml
git add Part3-RAG-Sales-Manual/rag-backend/activation_feature_service.py
git add Part3-RAG-Sales-Manual/ACTIVATION_UI_IMPROVEMENTS.md
git add Part3-RAG-Sales-Manual/deploy-activation-ui.ps1

# Show status
Write-Host ""
Write-Host "Git status:" -ForegroundColor Gray
git status --short

# Commit
Write-Host ""
Write-Host "Committing..." -ForegroundColor Gray
git commit -m "Add activation features UI with chunk_text and remove duplicate list"

# Push
Write-Host ""
Write-Host "Pushing to GitHub..." -ForegroundColor Gray
git push

Write-Host ""
Write-Host "✓ Git operations complete" -ForegroundColor Green
Write-Host ""

# Step 2: Deploy Backend (IMPORTANT - includes chunk_text field)
Write-Host "Step 2: Deploying Backend..." -ForegroundColor Yellow
Set-Location -Path "C:\Users\029878866\EMEA-AI-SQUAD\RAG-with-Notebook\Part3-RAG-Sales-Manual\rag-backend"

Write-Host "Starting backend build..." -ForegroundColor Gray
oc start-build rag-backend --follow

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "Restarting backend deployment..." -ForegroundColor Gray
    oc rollout restart deployment/rag-backend
    
    Write-Host ""
    Write-Host "Waiting for backend rollout..." -ForegroundColor Gray
    oc rollout status deployment/rag-backend
    
    Write-Host ""
    Write-Host "✓ Backend deployed successfully" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "✗ Backend build failed" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Waiting 10 seconds for backend to stabilize..." -ForegroundColor Gray
Start-Sleep -Seconds 10

# Step 3: Deploy Frontend
Write-Host "Step 3: Deploying Frontend..." -ForegroundColor Yellow
Set-Location -Path "C:\Users\029878866\EMEA-AI-SQUAD\RAG-with-Notebook\Part3-RAG-Sales-Manual\carbon-rag-ui"

Write-Host "Starting frontend build..." -ForegroundColor Gray
oc start-build carbon-rag-ui --follow

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "Restarting frontend deployment..." -ForegroundColor Gray
    oc rollout restart deployment/carbon-rag-ui
    
    Write-Host ""
    Write-Host "Waiting for frontend rollout..." -ForegroundColor Gray
    oc rollout status deployment/carbon-rag-ui
    
    Write-Host ""
    Write-Host "✓ Frontend deployed successfully" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "✗ Frontend build failed" -ForegroundColor Red
    exit 1
}

# Step 4: Update Route timeout
Write-Host ""
Write-Host "Step 4: Updating Route timeout..." -ForegroundColor Yellow
Write-Host "Applying route configuration..." -ForegroundColor Gray
oc apply -f openshift-deployment.yaml

Write-Host ""
Write-Host "✓ Route timeout updated to 60s" -ForegroundColor Green

# Step 5: Verify deployment
Write-Host ""
Write-Host "Step 5: Verifying deployment..." -ForegroundColor Yellow

Write-Host ""
Write-Host "Backend pods:" -ForegroundColor Gray
oc get pods | Select-String "rag-backend"

Write-Host ""
Write-Host "Frontend pods:" -ForegroundColor Gray
oc get pods | Select-String "carbon-rag-ui"

Write-Host ""
Write-Host "Route timeout:" -ForegroundColor Gray
oc get route carbon-rag-ui -o jsonpath='{.metadata.annotations.haproxy\.router\.openshift\.io/timeout}'
Write-Host ""

Write-Host ""
Write-Host "=== Deployment Complete ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "✓ Backend deployed (includes chunk_text field)" -ForegroundColor Green
Write-Host "✓ Frontend deployed (removed duplicate list)" -ForegroundColor Green
Write-Host "✓ Route timeout increased to 60s" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Test with query: 'E1080 activations'" -ForegroundColor White
Write-Host "2. Verify only ONE list appears (the interactive table)" -ForegroundColor White
Write-Host "3. Click on features to see Sales Manual chunk text" -ForegroundColor White
Write-Host "4. Compare LLM descriptions with source content" -ForegroundColor White
Write-Host ""
Write-Host "If issues occur, check logs:" -ForegroundColor Yellow
Write-Host "- Backend: oc logs -f deployment/rag-backend" -ForegroundColor White
Write-Host "- Frontend: oc logs -f deployment/carbon-rag-ui" -ForegroundColor White
Write-Host ""

# Made with Bob
