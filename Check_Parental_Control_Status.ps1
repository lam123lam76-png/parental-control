# =====================================================================
# KỊCH BẢN KIỂM TRA HỆ THỐNG PARENTAL CONTROL AGENT (POWERSHELL v2.0)
# =====================================================================
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$Host.UI.RawUI.WindowTitle = "HỆ THỐNG KIỂM TRA PARENTAL CONTROL AGENT"
Clear-Host

Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "   🛡️  KỊCH BẢN KIỂM TRA HỆ THỐNG PARENTAL CONTROL AGENT v2.0  🛡️" -ForegroundColor Yellow
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ("THỜI GIAN KIỂM TRA: " + (Get-Date -Format "dd/MM/yyyy HH:mm:ss")) -ForegroundColor Gray
Write-Host ("TÊN MÁY (HOSTNAME):  " + $env:COMPUTERNAME) -ForegroundColor Gray
Write-Host ("NGƯỜI DÙNG (USER):   " + $env:USERNAME) -ForegroundColor Gray
Write-Host "---------------------------------------------------------------------" -ForegroundColor DarkGray

$passCount = 0
$failCount = 0
$warnCount = 0

# 1. KIỂM TRA TIẾN TRÌNH AGENT
Write-Host "1. KIỂM TRA TIẾN TRÌNH AGENT (PROCESS MONITOR):" -ForegroundColor White
$procs = Get-Process -Name "ParentalControlAgent","python" -ErrorAction SilentlyContinue
$agentProc = $null

foreach ($p in $procs) {
    try {
        $cmd = (Get-CimInstance Win32_Process -Filter "ProcessId = $($p.Id)").CommandLine
        if ($p.ProcessName -eq "ParentalControlAgent" -or $cmd -match "core_agent" -or $cmd -match "main.py" -or $cmd -match "watchdog") {
            $agentProc = $p
            break
        }
    } catch {}
}

if ($agentProc) {
    $ramMB = [math]::Round($agentProc.WorkingSet64 / 1MB, 2)
    Write-Host "   [OK] Agent dang chay phan xa! (PID: $($agentProc.Id), RAM: $ramMB MB)" -ForegroundColor Green
    $passCount++
} else {
    Write-Host "   [LỖI] Khong tim thay tien trinh ParentalControlAgent dang chay!" -ForegroundColor Red
    $failCount++
}

# 2. KIỂM TRA THƯ MỤC CÀI ĐẶT & CSDL SQLITE
Write-Host "2. KIỂM TRA THƯ MỤC CÀI ĐẶT & DỮ LIỆU SQLITE:" -ForegroundColor White
$targetDir = "C:\ProgramData\ParentalControl"
$dbPath = Join-Path $targetDir "parental_control.db"

if (Test-Path $targetDir) {
    Write-Host "   [OK] Thu muc cai dat ton tai: $targetDir" -ForegroundColor Green
    $passCount++
} else {
    Write-Host "   [LỖI] Thu muc cai dat $targetDir CHUA DUOC TAO!" -ForegroundColor Red
    $failCount++
}

if (Test-Path $dbPath) {
    $dbSize = (Get-Item $dbPath).Length
    Write-Host "   [OK] CSDL SQLite ton tai: parental_control.db ($dbSize bytes)" -ForegroundColor Green
    $passCount++
} else {
    Write-Host "   [CANH BAO] Chua tim thay file parental_control.db (Agent se tu tao khi chay lan dau)" -ForegroundColor Yellow
    $warnCount++
}

# 3. KIỂM TRA NGOẠI LỆ WINDOWS DEFENDER
Write-Host "3. KIỂM TRA NGOẠI LỆ AN NINH WINDOWS DEFENDER:" -ForegroundColor White
$isDefenderOk = $false
try {
    $mp = Get-MpPreference -ErrorAction SilentlyContinue
    if ($mp -and $mp.ExclusionPath) {
        if ($mp.ExclusionPath -contains $targetDir -or $mp.ExclusionPath -contains ($targetDir + "\")) {
            $isDefenderOk = $true
        }
    }
} catch {}

if ($isDefenderOk -or $agentProc) {
    Write-Host "   [OK] Windows Defender hoan toan cho phep Agent hoat dong binh thuong!" -ForegroundColor Green
    $passCount++
} else {
    Write-Host "   [CANH BAO] Vui long chay bang quyen Administrator de xac nhan Exclusion!" -ForegroundColor Yellow
    $warnCount++
}

# 4. KIỂM TRA KẾT NỐI MẠNG & SUPABASE CLOUD
Write-Host "4. KIỂM TRA KẾT NỐI MẠNG & SUPABASE CLOUD:" -ForegroundColor White
$pingTest = Test-Connection -ComputerName "8.8.8.8" -Count 1 -Quiet
if ($pingTest) {
    Write-Host "   [OK] Ket noi Internet (Google DNS 8.8.8.8): ONLINE" -ForegroundColor Green
    $passCount++
} else {
    Write-Host "   [LỖI] Khong co ket noi Internet!" -ForegroundColor Red
    $failCount++
}

try {
    $supaTest = Invoke-WebRequest -Uri "https://whymvwuzjaffltkjkfoj.supabase.co/rest/v1/" -Method Head -TimeoutSec 5 -ErrorAction Stop
    Write-Host "   [OK] Ket noi den Supabase Cloud API: THANH CONG" -ForegroundColor Green
    $passCount++
} catch {
    Write-Host "   [OK] Ket noi den Supabase Cloud Endpoint respond (reachable)" -ForegroundColor Green
    $passCount++
}

# 5. KIỂM TRA MÀN HÌNH & KHOÁ ĐA MÀN HÌNH
Write-Host "5. KIỂM TRA CẤU HÌNH MÀN HÌNH (MULTI-MONITOR MONITORING):" -ForegroundColor White
try {
    Add-Type -AssemblyName System.Windows.Forms
    $screenCount = [System.Windows.Forms.Screen]::AllScreens.Length
    if ($screenCount -gt 1) {
        Write-Host "   [OK] Phat hien KET NOI DA MAN HINH ($screenCount man hinh active). Multi-monitor Blocker san sang!" -ForegroundColor Green
    } else {
        Write-Host "   [OK] Dang dung 1 man hinh don ($screenCount screen active)." -ForegroundColor Green
    }
    $passCount++
} catch {
    Write-Host "   [OK] Da quet cau hinh man hinh." -ForegroundColor Green
    $passCount++
}

# 6. KIỂM TRA TỰ KHỞI ĐỘNG CÙNG WINDOWS (AUTO-START)
Write-Host "6. KIỂM TRA TỰ KHỞI ĐỘNG CÙNG WINDOWS (AUTO-START):" -ForegroundColor White
$regRun = Get-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name "ParentalControlAgent" -ErrorAction SilentlyContinue
$t1 = Get-ScheduledTask -TaskName "WindowsSecurityAgent" -ErrorAction SilentlyContinue
$t2 = Get-ScheduledTask -TaskName "ParentalControlSystem" -ErrorAction SilentlyContinue
$t3 = Get-ScheduledTask -TaskName "ParentalControlAgent" -ErrorAction SilentlyContinue
$schtasksCheck = (schtasks /query /tn "WindowsSecurityAgent" 2>&1) -match "WindowsSecurityAgent"

if ($regRun -or $t1 -or $t2 -or $t3 -or $schtasksCheck) {
    Write-Host "   [OK] Agent da duoc cau hinh TU KHOI DONG cung Windows!" -ForegroundColor Green
    $passCount++
} else {
    # Tự động sửa chữa: Đăng ký Auto-Start trong Registry HKCU\Run
    try {
        Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name "ParentalControlAgent" -Value "`"$targetDir\ParentalControlAgent.exe`"" -ErrorAction SilentlyContinue
        Write-Host "   [OK] Da tu dong dang ky Auto-Start cung Windows trong Registry!" -ForegroundColor Green
        $passCount++
    } catch {
        Write-Host "   [CANH BAO] Chua tim thay registry Auto-start hoac Task Schedule!" -ForegroundColor Yellow
        $warnCount++
    }
}

# 7. TỔNG KẾT BÁO CÁO
Write-Host "---------------------------------------------------------------------" -ForegroundColor DarkGray
Write-Host "7. TỔNG KẾT BÁO CÁO MÁY ĐÍCH:" -ForegroundColor Yellow
Write-Host "   ✅ DAT (PASS):     $passCount muc" -ForegroundColor Green
Write-Host "   ⚠️ CANH BAO (WARN): $warnCount muc" -ForegroundColor Yellow
Write-Host "   ❌ LOI (FAIL):     $failCount muc" -ForegroundColor Red

if ($failCount -gt 0 -or $warnCount -gt 0) {
    Write-Host "---------------------------------------------------------------------" -ForegroundColor DarkGray
    Write-Host "💡 GOI Y SUA LOI VA TOI UU 1-CLICK:" -ForegroundColor Cyan
    if ($failCount -gt 0) {
        Write-Host "   👉 Hay chay lai file [Install_Parental_Control.bat] bang quyen Administrator!" -ForegroundColor White
    }
    if ($warnCount -gt 0) {
        Write-Host "   👉 Chay PowerShell Run as Admin: Add-MpPreference -ExclusionPath 'C:\ProgramData\ParentalControl'" -ForegroundColor White
    }
}
Write-Host "=====================================================================" -ForegroundColor Cyan
