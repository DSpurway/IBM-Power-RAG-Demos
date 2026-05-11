# Commit script - run from rag-backend directory
# This uses relative paths from the current location

Write-Host "=== Committing Code Changes ===" -ForegroundColor Cyan
Write-Host "Current directory: $(Get-Location)" -ForegroundColor Yellow

# Add files using relative paths (from rag-backend directory)
Write-Host "`nAdding modified files..." -ForegroundColor Yellow

git add query_classifier.py
git add watson_assistant_service.py
git add requirements.txt
git add WATSON_ASSISTANT_INTEGRATION.md
git add WATSON_CLARIFICATION_HANDLING.md
git add DEPLOY_NOW.md
git add test_watson_assistant.py

# Add files from parent directories
git add ../../.gitignore
git add ../../WATSON_ASSISTANT_AND_BUG_FIX_SUMMARY.md
git add ../../WATSON_INTEGRATION_COMPLETE.md
git add ../../DEPLOY_MANUAL_STEPS.md

Write-Host "Files staged" -ForegroundColor Green

# Commit
Write-Host "`nCommitting..." -ForegroundColor Yellow
git commit -m "Fix: Enhanced query classifier for 'stop supporting' queries + Watson Assistant integration

- Fixed bug where 'stop supporting' queries were misclassified as RAG
- Added patterns for 'stop supporting', 'end support', 'no longer support'
- Integrated Watson Assistant for superior NLP (optional)
- Added clarification handling for ambiguous server names
- Enhanced lifecycle field extraction
- Added comprehensive documentation
- Updated .gitignore to exclude credential files

Fixes issue where 'When did we stop supporting the S924?' returned 500 error"

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Committed successfully!" -ForegroundColor Green
    
    # Push
    Write-Host "`nPushing to Git..." -ForegroundColor Yellow
    git push
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Pushed to Git successfully!" -ForegroundColor Green
        Write-Host "`n✓ Watson credentials already set in OpenShift" -ForegroundColor Green
        Write-Host "✓ Build is running (rag-backend-15)" -ForegroundColor Green
        Write-Host "`nWait for build to complete, then test!" -ForegroundColor Cyan
    }
    else {
        Write-Host "✗ Push failed" -ForegroundColor Red
    }
}
else {
    Write-Host "✗ Commit failed or no changes" -ForegroundColor Yellow
}

# Made with Bob