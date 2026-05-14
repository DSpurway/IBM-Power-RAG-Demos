# Cleanup script to replace all "rag-backend" references with "rag-backend"
# This ensures consistent naming across all files

$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Cleaning up rag-backend references" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

$rootPath = $PSScriptRoot
$fileTypes = @("*.md", "*.ps1", "*.sh", "*.yaml", "*.yml")
$filesUpdated = 0

Write-Host "`nSearching for files to update..." -ForegroundColor Yellow

foreach ($fileType in $fileTypes) {
    $files = Get-ChildItem -Path $rootPath -Recurse -Include $fileType -File
    
    foreach ($file in $files) {
        $content = Get-Content $file.FullName -Raw -ErrorAction SilentlyContinue
        
        if ($content -and $content -match "rag-backend") {
            Write-Host "Updating: $($file.FullName.Replace($rootPath, '.'))" -ForegroundColor Green
            
            $newContent = $content -replace "rag-backend", "rag-backend"
            Set-Content -Path $file.FullName -Value $newContent -NoNewline
            
            $filesUpdated++
        }
    }
}

Write-Host "`n==========================================" -ForegroundColor Cyan
Write-Host "Cleanup complete!" -ForegroundColor Green
Write-Host "Files updated: $filesUpdated" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan

# Made with Bob
