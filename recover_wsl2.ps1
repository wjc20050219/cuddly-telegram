# recover_wsl2.ps1 —— 强制恢复卡死的 WSL 服务（必须以管理员身份运行）
# 用法（管理员 PowerShell）:
#   powershell -NoProfile -ExecutionPolicy Bypass -File D:\dsh\RiceVar-ID\recover_wsl2.ps1
# 全部过程写入 wsl_recovery.log，便于非提权会话事后查看。
# 设计原则：先强杀进程再重启服务（服务卡死时 Stop-Service 自己也会挂住）。

$ErrorActionPreference = 'Continue'
$log = 'D:\dsh\RiceVar-ID\wsl_recovery.log'
$env:WSL_UTF8 = '1'

function L($m) { Add-Content -Path $log -Value ("{0}  {1}" -f (Get-Date -Format 'HH:mm:ss'), $m) -Encoding utf8 }

Set-Content -Path $log -Value "===== WSL 恢复开始 $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') =====" -Encoding utf8

# ---------- 0. 确认提权 ----------
$cur = [Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
$elevated = $cur.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
L "已提权: $elevated"
if (-not $elevated) {
  L "!! 未提权，无法恢复。请以管理员身份重新运行本脚本。"
  exit 1
}

# ---------- 1. 恢复前快照 ----------
L ""
L "--- 恢复前 ---"
foreach ($svc in 'WslService','vmcompute','hns') {
  $s = Get-Service $svc -ErrorAction SilentlyContinue
  L ("  服务 {0,-12} {1}" -f $svc, $(if ($s) { $s.Status } else { '(不存在)' }))
}
Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'wsl|vmmem' } |
  ForEach-Object { L "  进程 $($_.Name) PID=$($_.ProcessId)" }

# ---------- 2. 强杀 WSL 相关进程 ----------
L ""
L "--- 第 1 步：强制结束 WSL 进程 ---"
foreach ($n in 'wslservice','vmmemWSL','wslsettings','wslhost','wslrelay','wsl') {
  $out = (& taskkill.exe /F /IM "$n.exe" 2>&1 | Out-String).Trim()
  if ($out) { L "  [$n] $out" }
}
Start-Sleep -Seconds 3

# 二次确认：还有残留就按 PID 再杀一次
$left = Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.ProcessName -match 'wsl|vmmem' }
if ($left) {
  L "  仍有残留，按 PID 再杀: $(($left | ForEach-Object { $_.ProcessName + '=' + $_.Id }) -join ', ')"
  $left | Stop-Process -Force -ErrorAction SilentlyContinue
  Start-Sleep -Seconds 3
}

# ---------- 3. 重启依赖服务 ----------
L ""
L "--- 第 2 步：重启 vmcompute / hns / WslService ---"
foreach ($svc in 'vmcompute','hns','WslService') {
  $ok = $false
  try { Restart-Service $svc -Force -ErrorAction Stop; $ok = $true }
  catch {
    L "  $svc 重启失败: $($_.Exception.Message)"
    try { Start-Service $svc -ErrorAction Stop; $ok = $true }
    catch { L "  $svc 启动也失败: $($_.Exception.Message)" }
  }
  if ($ok) {
    $st = (Get-Service $svc -ErrorAction SilentlyContinue).Status
    L "  $svc -> $st"
  }
}
Start-Sleep -Seconds 6

# ---------- 4. 恢复后快照 ----------
L ""
L "--- 恢复后 ---"
foreach ($svc in 'WslService','vmcompute','hns') {
  $s = Get-Service $svc -ErrorAction SilentlyContinue
  L ("  服务 {0,-12} {1}" -f $svc, $(if ($s) { $s.Status } else { '(不存在)' }))
}
Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'wsl|vmmem' } |
  ForEach-Object { L "  进程 $($_.Name) PID=$($_.ProcessId)" }

# ---------- 5. 关闭残留 WSL 实例 ----------
L ""
L "--- 第 3 步：wsl --shutdown ---"
$job = Start-Job { $env:WSL_UTF8='1'; & wsl.exe --shutdown 2>&1 | Out-String }
if (Wait-Job $job -Timeout 45) {
  L ("  " + ((Receive-Job $job | Out-String).Trim()))
} else { L "  ✗ --shutdown 超时（45 秒），已放弃"; Stop-Job $job }
Remove-Job $job -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 4

# ---------- 6. 验证 ----------
L ""
L "--- 第 4 步：验证 wsl -l -v ---"
$job = Start-Job { $env:WSL_UTF8='1'; & wsl.exe -l -v 2>&1 | Out-String }
if (Wait-Job $job -Timeout 60) {
  $r = (Receive-Job $job | Out-String).Trim()
  if ($r) { L "  ✅ 有响应："; ($r -split "`n") | ForEach-Object { L "    $($_.TrimEnd())" } }
  else { L "  ⚠️ 命令返回但无输出" }
} else { L "  ✗ wsl -l -v 仍无响应（60 秒超时）"; Stop-Job $job }
Remove-Job $job -Force -ErrorAction SilentlyContinue

L ""
L "===== 恢复流程结束 $(Get-Date -Format 'HH:mm:ss') ====="

# 结束后不要自动关闭窗口，方便查看
if ($Host.Name -eq 'ConsoleHost' -and -not $env:RV_NOPAUSE) {
  Write-Host ""
  Write-Host "完成。日志: $log" -ForegroundColor Green
  Write-Host "按任意键关闭..." -ForegroundColor DarkGray
  try { $null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown') } catch {}
}
