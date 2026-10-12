# TestHive prerequisites for Windows (uses winget).
# Usage: powershell -ExecutionPolicy Bypass -File scripts\setup.ps1 [-Check | -Install] [-Web]
#   -Check    (default) report what is missing, install nothing; writes .testhive-ready when all required tools are present
#   -Install  install what is missing (run only after the user agreed)
#   -Web      also check/install Playwright (web tests, in web\)
param([switch]$Check, [switch]$Install, [switch]$Web)
$mode = if ($Install) { 'install' } else { 'check' }
function Have($c) { [bool](Get-Command $c -ErrorAction SilentlyContinue) }
function JavaOk { if (-not (Have java)) { return $false }; $v = ("$(& java -version 2>&1 | Select-Object -First 1)") -replace '[^"]*"(\d+).*','$1'; return (($v -as [int]) -ge 17) }
# A python that really runs: the Microsoft Store stub exists on PATH but does nothing.
function PyOk {
  foreach ($c in 'python','python3','py') {
    if (Have $c) { try { & $c -c 'import sys; sys.exit(sys.version_info[0] != 3)' 2>$null | Out-Null; if ($LASTEXITCODE -eq 0) { return $true } } catch {} }
  }
  return $false
}
$tools = @(
  @{n='git';     ok={Have git};     id='Git.Git'},
  @{n='node';    ok={Have node};    id='OpenJS.NodeJS.LTS'},
  @{n='python';  ok={PyOk};         id='Python.Python.3.12'},
  @{n='java17';  ok={JavaOk};       id='EclipseAdoptium.Temurin.17.JDK'},
  @{n='adb';     ok={Have adb};     id='Google.PlatformTools'},
  @{n='maestro'; ok={Have maestro}; id=$null},
  @{n='newman';  ok={Have newman};  npm='newman'},
  @{n='claude';  ok={Have claude};  npm='@anthropic-ai/claude-code'}
)
if ($Web) { $tools += @{n='playwright'; ok={Test-Path 'web/node_modules/@playwright/test'}} }
function Report { $script:missing = @(); foreach ($t in $tools) { if (& $t.ok) { "OK       $($t.n)" } else { "MISSING  $($t.n)"; $script:missing += $t } } }
function Install-Maestro {
  $dir = Join-Path $env:USERPROFILE 'maestro'
  $zip = Join-Path $env:TEMP 'maestro.zip'
  Invoke-WebRequest 'https://github.com/mobile-dev-inc/maestro/releases/latest/download/maestro.zip' -OutFile $zip
  Expand-Archive $zip -DestinationPath $dir -Force
  $bin = Join-Path $dir 'maestro\bin'
  $old = [Environment]::GetEnvironmentVariable('Path','User')
  [Environment]::SetEnvironmentVariable('Path', (@($old, $bin) | Where-Object { $_ }) -join ';', 'User')
  Write-Host "  Maestro placed in $bin and added to your PATH. Open a new terminal."
}
Write-Host "TestHive setup ($mode) on Windows"
Report
if ($missing.Count -eq 0) { if (-not $Web) { (Get-Date).ToUniversalTime().ToString('s') + 'Z' | Set-Content .testhive-ready }; Write-Host 'All prerequisites present.' }
elseif ($mode -eq 'install') {
  foreach ($t in $missing) {
    Write-Host "Installing $($t.n) ..."
    try {
      if ($t.n -eq 'maestro') { Install-Maestro }
      elseif ($t.n -eq 'playwright') { Push-Location web; try { npm install; npx playwright install chromium } finally { Pop-Location } }
      elseif ($t.npm) { npm install -g $t.npm }
      else { winget install --id $t.id -e --accept-source-agreements --accept-package-agreements }
    } catch { Write-Host "  FAILED $($t.n): $_" }
  }
  Write-Host '--- open a NEW terminal, then run: powershell -ExecutionPolicy Bypass -File scripts\setup.ps1 -Check ---'
} else { Write-Host ('Missing: ' + (($missing | ForEach-Object { $_.n }) -join ', ')); Write-Host 'Run: powershell -ExecutionPolicy Bypass -File scripts\setup.ps1 -Install' }
Write-Host @'

Manual steps no script can do:
  Android: enable Developer options + USB debugging on the phone, connect by USB, accept the prompt.
  iOS needs a Mac (or a cloud Mac / device farm). Windows cannot run the iOS Simulator.
  Claude Code: first start asks you to sign in.
  The other scripts are bash: run them from Git Bash (installed with Git), e.g. bash scripts/check-devices.sh
'@
exit ($missing.Count)
