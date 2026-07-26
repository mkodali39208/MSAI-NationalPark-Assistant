$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

if (-not (Test-Path ".\.venv\Scripts\Activate.ps1")) {
    throw "Virtual environment not found at .venv. Run this script from the project root."
}

Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
. .\.venv\Scripts\Activate.ps1

python tools\patch_existing_files.py
Set-Location data_ingestion
python scrape_extended_nps.py
python build_extended_chunks.py

Write-Host ""
Write-Host "Now run: python create_embeddings.py" -ForegroundColor Yellow
Write-Host "When asked to recreate the collection, enter y." -ForegroundColor Yellow
Write-Host "Then run: python create_index.py" -ForegroundColor Yellow
Write-Host "Then run: python audit_question_coverage.py" -ForegroundColor Yellow
