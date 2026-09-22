# recover_wsl.ps1 - restart the wedged WSL service and verify (run elevated)
$log = 'D:\dsh\RiceVar-ID\wsl_recovery.log'
$env:WSL_UTF8 = '1'
function L($m) { $line = "[{0}] {1}" -f (Get-Date -Format 'HH:mm:ss'), $m; Add-Content -LiteralPath $log -Value $line -Encoding UTF8; Write-Host $line }

Set-Content -LiteralPath $log -Value '===== WSL recovery =====' -Encoding UTF8
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
L ("elevated=" + $isAdmin)

L '--- kill leftover wsl/wslhost processes ---'
foreach ($n in 'wsl','wslhost','wslsettings') {
    Get-Process -Name $n -ErrorAction SilentlyContinue | ForEach-Object {
        try { Stop-Process -Id $_.Id -Force -ErrorAction Stop; L ("killed $n $($_.Id)") } catch { L ("cannot kill $n $($_.Id): $($_.Exception.Message)") }
    }
}

L '--- restart services ---'
foreach ($svc in 'WslService','vmcompute','hns') {
    $s = Get-Service -Name $svc -ErrorAction SilentlyContinue
    if (-not $s) { L "$svc NOT_EXIST"; continue }
    try {
        if ($s.Status -eq 'Running') { Stop-Service -Name $svc -Force -ErrorAction Stop; L "$svc stopped" }
        Start-Service -Name $svc -ErrorAction Stop; L "$svc started"
    } catch { L "$svc FAILED: $($_.Exception.Message)" }
}
Start-Sleep -Seconds 5

L '--- wsl --shutdown ---'
$p = Start-Process -FilePath 'wsl.exe' -ArgumentList '--shutdown' -PassThru -WindowStyle Hidden
if ($p.WaitForExit(45000)) { L "shutdown exit=$($p.ExitCode)" } else { L 'shutdown TIMED OUT'; try { $p.Kill() } catch {} }
Start-Sleep -Seconds 5

L '--- probe: wsl -l -v ---'
$out = Join-Path $env:TEMP 'recover_probe.txt'
$err = Join-Path $env:TEMP 'recover_probe.err'
$p2 = Start-Process -FilePath 'wsl.exe' -ArgumentList '-l','-v' -PassThru -WindowStyle Hidden -RedirectStandardOutput $out -RedirectStandardError $err
if ($p2.WaitForExit(60000)) {
    L "probe exit=$($p2.ExitCode)"
    if (Test-Path $out) { L ('STDOUT: ' + ((Get-Content $out -Raw) -replace "`0",'')) }
    if (Test-Path $err) { L ('STDERR: ' + ((Get-Content $err -Raw) -replace "`0",'')) }
} else { L 'probe TIMED OUT AGAIN'; try { $p2.Kill() } catch {} }

L '--- smoke test inside distro ---'
$p3 = Start-Process -FilePath 'wsl.exe' -ArgumentList '-d','Ubuntu','-u','root','--','bash','-lc','source /opt/miniconda3/etc/profile.d/conda.sh && conda activate ricevar && python -V && samtools --version | head -n1 && nproc && free -h | head -n2' -PassThru -WindowStyle Hidden -RedirectStandardOutput $out -RedirectStandardError $err
if ($p3.WaitForExit(120000)) {
    L "smoke exit=$($p3.ExitCode)"
    if (Test-Path $out) { L ('OUT: ' + ((Get-Content $out -Raw) -replace "`0",'')) }
} else { L 'smoke TIMED OUT'; try { $p3.Kill() } catch {} }

L 'ALL_DONE'
