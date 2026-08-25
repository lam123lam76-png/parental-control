# ============================================================
#  SETUP Watchdog Scheduled Task — run with Administrator
#  (right-click fix_watchdog_task.bat -> Run as administrator)
#
#  Creates the watchdog task so the agent starts right after the
#  user logs on (AtLogOn) + self-heals every 2 minutes.
#  Battery-safe + RunLevel Highest (fallback Limited).
#  No password needed — the task runs only in the user session.
# ============================================================
$ErrorActionPreference = 'Stop'

Write-Host '== Setup Watchdog Scheduled Task (start at logon) ==' -ForegroundColor Cyan
Write-Host ''

# 1. Remove the old task (ignore errors if absent)
try {
    Unregister-ScheduledTask -TaskName 'ParentalControlWatchdogTask' -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host '[1/3] Old task removed (or was absent).'
} catch {
    Write-Host ('[1/3] Unregister note: ' + $_.Exception.Message)
}

# 2. Build the new task: AtLogOn + 2-min repetition, battery-safe
$action   = New-ScheduledTaskAction -Execute 'C:\ProgramData\ParentalControl\ParentalControlWatchdog.exe'
$tLogon   = New-ScheduledTaskTrigger -AtLogOn
$tRepeat  = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 2)
$who      = '{0}\{1}' -f $env:USERDOMAIN, $env:USERNAME
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 0)

$registered = $false
foreach ($level in 'Highest', 'Limited') {
    try {
        $principal = New-ScheduledTaskPrincipal -UserId $who -LogonType Interactive -RunLevel $level
        Register-ScheduledTask -TaskName 'ParentalControlWatchdogTask' `
            -Action $action -Trigger $tLogon, $tRepeat -Principal $principal -Settings $settings `
            -Force -ErrorAction Stop | Out-Null
        Write-Host ("[2/3] Task registered (RunLevel = {0}, AtLogOn, battery-safe)." -f $level) -ForegroundColor Green
        $registered = $true
        break
    } catch {
        Write-Host ("[2/3] RunLevel {0} failed: {1}" -f $level, $_.Exception.Message)
    }
}

if (-not $registered) {
    Write-Host '[2/3] FAILED: could not register task. Make sure this runs as Administrator.' -ForegroundColor Red
}

# 3. Verify
Start-Sleep -Milliseconds 500
$t = Get-ScheduledTask -TaskName 'ParentalControlWatchdogTask' -ErrorAction SilentlyContinue
if ($t) {
    Write-Host '[3/3] Verification:' -ForegroundColor Cyan
    Write-Host ("      RunLevel    : {0}" -f $t.Principal.RunLevel)
    Write-Host ("      DisallowBatt: {0}  StopOnBatt: {1}" -f $t.Settings.DisallowStartIfOnBatteries, $t.Settings.StopIfGoingOnBatteries)
    Write-Host ("      Triggers    : {0}" -f $t.Triggers.Count)
    Write-Host ("      Action      : {0}" -f $t.Actions.Execute)
    Write-Host '      OK - agent will start right after user logon.' -ForegroundColor Green
} else {
    Write-Host '[3/3] ERROR: task not found after registration.' -ForegroundColor Red
}

Write-Host ''
pause
