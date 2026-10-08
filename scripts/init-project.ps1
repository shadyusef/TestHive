# Usage: powershell -File scripts/init-project.ps1 "<PROJECT_NAME>"
param([Parameter(Mandatory=$true)][string]$Name)
New-Item -ItemType Directory -Force workflow,test-cases,reports,reviews | Out-Null
if (-not (Test-Path PROJECT_BRIEF.md)) { (Get-Content templates/PROJECT_BRIEF.md) -replace '<PROJECT_NAME>',$Name | Set-Content PROJECT_BRIEF.md }
if (-not (Test-Path workflow/BOARD.md)) { Copy-Item templates/BOARD.md workflow/BOARD.md }
if (-not (Test-Path test-cases/TestCases.csv)) { Copy-Item templates/TestCases.csv test-cases/TestCases.csv }
if (-not (Test-Path .env)) { Copy-Item templates/env.example .env }
Write-Host "Project '$Name' initialised. Next: edit PROJECT_BRIEF.md and .env, then run scripts/check-devices.sh"
