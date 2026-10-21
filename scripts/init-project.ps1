# Usage: powershell -ExecutionPolicy Bypass -File scripts/init-project.ps1 "<PROJECT_NAME>"
param([Parameter(Mandatory=$true)][string]$Name)
New-Item -ItemType Directory -Force workflow/intake,test-cases,reports,reviews,mobile/data,requirements/sources,analysis,runs | Out-Null
if (-not (Test-Path PROJECT_BRIEF.md)) { (Get-Content templates/PROJECT_BRIEF.md -Encoding UTF8).Replace('<PROJECT_NAME>', $Name) | Set-Content PROJECT_BRIEF.md -Encoding UTF8 }
if (-not (Test-Path workflow/BOARD.md)) { Copy-Item templates/BOARD.md workflow/BOARD.md }
if (-not (Test-Path test-cases/TestCases.csv)) { Copy-Item templates/TestCases.csv test-cases/TestCases.csv }
if (-not (Test-Path .env)) { Copy-Item templates/env.example .env }
if (-not (Test-Path CONTEXT.md)) { Copy-Item templates/CONTEXT.md CONTEXT.md }
if (-not (Test-Path analysis/requirements.csv)) { Get-Content templates/requirements.csv -TotalCount 1 -Encoding UTF8 | Set-Content analysis/requirements.csv -Encoding UTF8 }
if (-not (Test-Path analysis/gaps.csv)) { Get-Content templates/gaps.csv -TotalCount 1 -Encoding UTF8 | Set-Content analysis/gaps.csv -Encoding UTF8 }
Write-Host "Project '$Name' initialised. Next: edit PROJECT_BRIEF.md, CONTEXT.md and .env, then run scripts/setup.ps1 -Check (first time) and bash scripts/check-devices.sh"
