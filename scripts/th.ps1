# Usage: .\scripts\th.ps1 <agent> ["task"]   (agents: lead manual mobile api web data triage review)
# Headless runs (with a task) use --permission-mode acceptEdits; override with $env:TH_PERMISSION_MODE.
param([Parameter(Mandatory=$true)][string]$Agent, [Parameter(ValueFromRemainingArguments=$true)][string[]]$Task)
$map = @{lead='testhive-lead';manual='manual-tester';mobile='mobile-automation-engineer';api='api-backend-test-engineer';web='web-automation-engineer';data='test-data-env-manager';triage='defect-triage';review='qa-reviewer'}
$a = if ($map.ContainsKey($Agent)) { $map[$Agent] } else { $Agent }
if (-not (Test-Path ".claude/agents/$a.md")) { Write-Error "Unknown agent: $a"; exit 1 }
$mode = if ($env:TH_PERMISSION_MODE) { $env:TH_PERMISSION_MODE } else { 'acceptEdits' }
if ($Task) { claude --agent $a --permission-mode $mode -p ($Task -join ' ') } else { claude --agent $a }
