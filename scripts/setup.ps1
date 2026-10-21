# TestHive prerequisites for Windows (uses winget).
# Usage: powershell -ExecutionPolicy Bypass -File scripts\setup.ps1 [-Check | -Install] [-Web] [-Ocr] [-AddBashToPath]
#   -Check          (default) report what is missing, install nothing; writes .testhive-ready when all required tools are present
#   -Install        install what is missing (run only after the user agreed)
#   -Web            also check/install Playwright (web tests, in web\)
#   -Ocr            also check/install Tesseract OCR with Arabic (image masking); otherwise reported as optional
#   -AddBashToPath  add Git Bash to your user PATH, so "bash scripts/..." works in PowerShell (.\hive works without it)
param([switch]$Check, [switch]$Install, [switch]$Web, [switch]$Ocr, [switch]$AddBashToPath)
$mode = if ($Install) { 'install' } else { 'check' }
function Have($c) { [bool](Get-Command $c -ErrorAction SilentlyContinue) }
function JavaOk { if (-not (Have java)) { return $false }; $v = ("$(& java -version 2>&1 | Select-Object -First 1)") -replace '[^"]*"(\d+).*','$1'; return (($v -as [int]) -ge 17) }
# A python that really runs: the Microsoft Store stub exists on PATH but does nothing.
function PyCmd {
  foreach ($c in 'python','python3','py') {
    if (Have $c) { try { & $c -c 'import sys; sys.exit(sys.version_info[0] != 3)' 2>$null | Out-Null; if ($LASTEXITCODE -eq 0) { return $c } } catch {} }
  }
  return $null
}
$pyPkgs = 'openpyxl','pypdf','python-docx','pillow','pytesseract'
function PyPkgsOk { $p = PyCmd; if (-not $p) { return $false }; & $p -c 'import openpyxl, pypdf, docx, PIL, pytesseract' 2>$null | Out-Null; return ($LASTEXITCODE -eq 0) }
function TessExe { if (Have tesseract) { return 'tesseract' }; $p = Join-Path $env:ProgramFiles 'Tesseract-OCR\tesseract.exe'; if (Test-Path $p) { return $p }; return $null }
function OcrOk { $t = TessExe; if (-not $t) { return $false }; return [bool]((& $t --list-langs 2>$null) -match '^ara$') }
function GitBashDir {
  $g = Get-Command git -ErrorAction SilentlyContinue
  $c = @(); if ($g) { $c += (Join-Path (Split-Path (Split-Path $g.Source)) 'bin') }
  $c += (Join-Path $env:ProgramFiles 'Git\bin'), (Join-Path $env:LOCALAPPDATA 'Programs\Git\bin')
  foreach ($d in $c) { if (Test-Path (Join-Path $d 'bash.exe')) { return $d } }
  return $null
}
$tools = @(
  @{n='git';         ok={Have git};     id='Git.Git'},
  @{n='node';        ok={Have node};    id='OpenJS.NodeJS.LTS'},
  @{n='python';      ok={[bool](PyCmd)}; id='Python.Python.3.12'},
  @{n='python-pkgs'; ok={PyPkgsOk};     pip=$true},
  @{n='java17';      ok={JavaOk};       id='EclipseAdoptium.Temurin.17.JDK'},
  @{n='adb';         ok={Have adb};     id='Google.PlatformTools'},
  @{n='maestro';     ok={Have maestro}; id=$null},
  @{n='newman';      ok={Have newman};  npm='newman'},
  @{n='claude';      ok={Have claude};  npm='@anthropic-ai/claude-code'}
)
if ($Web) { $tools += @{n='playwright'; ok={Test-Path 'web/node_modules/@playwright/test'}} }
if ($Ocr) { $tools += @{n='tesseract'; ok={OcrOk}; id='UB-Mannheim.TesseractOCR'} }
function Report {
  $script:missing = @()
  foreach ($t in $tools) { if (& $t.ok) { "OK       $($t.n)" } else { "MISSING  $($t.n)"; $script:missing += $t } }
  if (-not $Ocr) { if (OcrOk) { 'OK       tesseract (with Arabic)' } else { 'OPTIONAL tesseract + Arabic (image masking): add -Install -Ocr' } }
}
function Install-Maestro {
  $dir = Join-Path $env:USERPROFILE 'maestro'
  $zip = Join-Path $env:TEMP 'maestro.zip'
  Invoke-WebRequest 'https://github.com/mobile-dev-inc/maestro/releases/latest/download/maestro.zip' -OutFile $zip
  Expand-Archive $zip -DestinationPath $dir -Force
  Add-UserPath (Join-Path $dir 'maestro\bin')
  Write-Host "  Maestro installed and added to your PATH. Open a new terminal."
}
function Add-UserPath($d) {
  $old = [Environment]::GetEnvironmentVariable('Path','User')
  if (($old -split ';') -contains $d) { return }
  [Environment]::SetEnvironmentVariable('Path', (@($old, $d) | Where-Object { $_ }) -join ';', 'User')
}
# Arabic OCR data goes in a user folder (no admin rights needed), next to the English data that Tesseract ships.
function Install-ArabicOcr {
  $t = TessExe; if (-not $t) { Write-Host '  Tesseract not found after install: open a new terminal and run -Check'; return }
  $dir = Join-Path $env:LOCALAPPDATA 'TestHive\tessdata'; New-Item -ItemType Directory -Force $dir | Out-Null
  $src = Join-Path (Split-Path ((Get-Command $t).Source)) 'tessdata'
  foreach ($f in 'eng.traineddata','osd.traineddata') { if ((Test-Path (Join-Path $src $f)) -and -not (Test-Path (Join-Path $dir $f))) { Copy-Item (Join-Path $src $f) $dir } }
  $ara = Join-Path $dir 'ara.traineddata'
  if (-not (Test-Path $ara)) { Invoke-WebRequest 'https://github.com/tesseract-ocr/tessdata_fast/raw/main/ara.traineddata' -OutFile $ara }
  [Environment]::SetEnvironmentVariable('TESSDATA_PREFIX', $dir, 'User'); $env:TESSDATA_PREFIX = $dir
  Write-Host "  Arabic OCR data placed in $dir (TESSDATA_PREFIX set for your user)."
}
Write-Host "TestHive setup ($mode) on Windows"
if ($AddBashToPath) {
  $b = GitBashDir
  if ($b) { Add-UserPath $b; Write-Host "Git Bash ($b) is on your PATH. Open a new terminal, then 'bash scripts/...' works." }
  else { Write-Host 'Git Bash not found: install Git first.' }
}
Report
if ($missing.Count -eq 0) { if (-not $Web) { (Get-Date).ToUniversalTime().ToString('s') + 'Z' | Set-Content .testhive-ready }; Write-Host 'All prerequisites present.' }
elseif ($mode -eq 'install') {
  foreach ($t in $missing) {
    Write-Host "Installing $($t.n) ..."
    try {
      if ($t.n -eq 'maestro') { Install-Maestro }
      elseif ($t.n -eq 'playwright') { Push-Location web; try { npm install; npx playwright install chromium } finally { Pop-Location } }
      elseif ($t.pip) { $p = PyCmd; if ($p) { & $p -m pip install --user @pyPkgs } else { Write-Host '  Install python first' } }
      elseif ($t.npm) { npm install -g $t.npm }
      else {
        if (-not (TessExe) -or $t.n -ne 'tesseract') { winget install --id $t.id -e --source winget --accept-source-agreements --accept-package-agreements }
        if ($t.n -eq 'tesseract') { Install-ArabicOcr }
      }
    } catch { Write-Host "  FAILED $($t.n): $_" }
  }
  Write-Host '--- open a NEW terminal, then run: powershell -ExecutionPolicy Bypass -File scripts\setup.ps1 -Check ---'
} else { Write-Host ('Missing: ' + (($missing | ForEach-Object { $_.n }) -join ', ')); Write-Host 'Run: powershell -ExecutionPolicy Bypass -File scripts\setup.ps1 -Install' }
Write-Host @'

Manual steps no script can do:
  Android: enable Developer options + USB debugging on the phone, connect by USB, accept the prompt.
  iOS needs a Mac (or a cloud Mac / device farm). Windows cannot run the iOS Simulator.
  Claude Code: first start asks you to sign in.
  The other scripts are bash. From PowerShell run them with the launcher: .\hive <script> ...  (e.g. .\hive stage status)
'@
exit ($missing.Count)
