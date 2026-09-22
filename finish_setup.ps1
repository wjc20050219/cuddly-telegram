# RiceVar-ID: post-reboot WSL2 + Miniforge + conda environment setup
# ASCII-only on purpose (encoding safety). Run elevated.
# Log: D:\dsh\RiceVar-ID\post_reboot.log  (UTF-8)

# Make wsl.exe emit UTF-8 instead of UTF-16LE (honoured by modern wsl; harmless otherwise)
$env:WSL_UTF8 = '1'

$repo = 'D:\dsh\RiceVar-ID'
$log  = Join-Path $repo 'post_reboot.log'

function L {
    param([string]$m)
    $line = '[{0}] {1}' -f (Get-Date -Format 'HH:mm:ss'), $m
    Add-Content -LiteralPath $log -Value $line -Encoding UTF8
    Write-Host $line
}

# Fallback decoder for the case where wsl ignores WSL_UTF8 and emits UTF-16LE.
function Convert-Output {
    param([byte[]]$bytes)
    if (-not $bytes -or $bytes.Length -eq 0) { return '' }
    if ($bytes.Length -ge 2 -and $bytes[0] -eq 0xFF -and $bytes[1] -eq 0xFE) {
        return [System.Text.Encoding]::Unicode.GetString($bytes, 2, $bytes.Length - 2)
    }
    if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
        return [System.Text.Encoding]::UTF8.GetString($bytes, 3, $bytes.Length - 3)
    }
    $n = [Math]::Min(24, $bytes.Length - ($bytes.Length % 2))
    $oddZero = 0; $oddTotal = 0
    for ($i = 1; $i -lt $n; $i += 2) { $oddTotal++; if ($bytes[$i] -eq 0) { $oddZero++ } }
    if ($oddTotal -gt 0 -and $oddZero -ge [Math]::Ceiling($oddTotal * 0.6)) {
        return [System.Text.Encoding]::Unicode.GetString($bytes)
    }
    return [System.Text.Encoding]::UTF8.GetString($bytes)
}

function Invoke-Direct {
    param([string]$Exe, [string[]]$Arguments)
    L ('RUN> ' + $Exe + ' ' + ($Arguments -join ' '))
    $tmp = Join-Path $env:TEMP ('dsh_' + [guid]::NewGuid().ToString('N') + '.out')
    $quoted = ($Arguments | ForEach-Object {
        if ($_ -match '[\s"]') { '"' + ($_ -replace '"', '\"') + '"' } else { $_ }
    }) -join ' '
    cmd.exe /c "$Exe $quoted > `"$tmp`" 2>&1"
    $code = $LASTEXITCODE
    $bytes = @()
    if (Test-Path -LiteralPath $tmp) { $bytes = [System.IO.File]::ReadAllBytes($tmp) }
    Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue
    $text = Convert-Output $bytes
    if ($text -and $text.Trim().Length -gt 0) {
        Add-Content -LiteralPath $log -Value $text.TrimEnd() -Encoding UTF8
    }
    L ('EXIT=' + $code)
    return [pscustomobject]@{ Code = $code; Text = $text }
}

Set-Content -LiteralPath $log -Value '===== RiceVar-ID post-reboot setup =====' -Encoding UTF8
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
L ('elevated=' + $isAdmin)

L '--- STEP 0: services ---'
foreach ($svc in 'LxssManager','WslService','vmcompute') {
    $s = Get-Service -Name $svc -ErrorAction SilentlyContinue
    if ($s) { L ($svc + ': ' + $s.Status) } else { L ($svc + ': NOT_EXIST') }
}

L '--- STEP 1: wsl probe under elevation ---'
$st = Invoke-Direct 'wsl.exe' @('--status')
$lv = Invoke-Direct 'wsl.exe' @('-l','-v')

L '--- STEP 2: install latest WSL package (best effort) ---'
$u = Invoke-Direct 'wsl.exe' @('--update','--web-download')
if ($u.Code -ne 0) {
    L 'web-download failed; trying inbox kernel update'
    Invoke-Direct 'wsl.exe' @('--update','--inbox') | Out-Null
}
Invoke-Direct 'wsl.exe' @('--version') | Out-Null

L '--- STEP 3: default version 2 ---'
Invoke-Direct 'wsl.exe' @('--set-default-version','2') | Out-Null

L '--- STEP 4: install Ubuntu distro (no launch) ---'
$inst = Invoke-Direct 'wsl.exe' @('--install','-d','Ubuntu','--no-launch')
if ($inst.Code -ne 0) {
    L 'retry 1: wsl --install -d Ubuntu'
    $inst = Invoke-Direct 'wsl.exe' @('--install','-d','Ubuntu')
}
if ($inst.Code -ne 0) {
    L 'retry 2: wsl --install -d Ubuntu-24.04'
    $inst = Invoke-Direct 'wsl.exe' @('--install','-d','Ubuntu-24.04','--no-launch')
}

L '--- STEP 5: distro list ---'
$lv2 = Invoke-Direct 'wsl.exe' @('-l','-v')

$haveUbuntu = ($lv2.Text -match 'Ubuntu') -or ($lv.Text -match 'Ubuntu')
if (-not $haveUbuntu) {
    L 'NO_UBUNTU_REGISTERED -> skipping environment build'
    L 'ALL_DONE_WITH_ERRORS'
    exit 1
}
L 'Ubuntu is registered'

L '--- STEP 6: root shell check inside Ubuntu ---'
$root = Invoke-Direct 'wsl.exe' @('-d','Ubuntu','-u','root','--','id','-u')
if ($root.Code -ne 0) { L 'WARNING: root shell unavailable; OOBE may be pending' }

L '--- STEP 7: build conda environment inside WSL (long running) ---'
$sh = Join-Path $repo 'setup_wsl_env.sh'
if (-not (Test-Path -LiteralPath $sh)) {
    L ('MISSING SCRIPT: ' + $sh)
    L 'ALL_DONE_WITH_ERRORS'
    exit 1
}
# normalize to LF without BOM: bash rejects CRLF shebangs
$txt = [System.IO.File]::ReadAllText($sh) -replace "`r`n", "`n"
[System.IO.File]::WriteAllText($sh, $txt, (New-Object System.Text.UTF8Encoding($false)))

$inner = 'wsl.exe -d Ubuntu -u root -- bash /mnt/d/dsh/RiceVar-ID/setup_wsl_env.sh'
L 'progress is streamed to this window and to wsl_env_setup.log (UTF-8)'
L ('RUN> cmd.exe /c "chcp 65001 >nul && ' + $inner + '"')
cmd.exe /c "chcp 65001 >nul && $inner"
L ('EXIT=' + $LASTEXITCODE)

L '--- STEP 8: final verification ---'
Invoke-Direct 'wsl.exe' @('-d','Ubuntu','-u','root','--','/opt/miniforge3/bin/conda','env','list') | Out-Null

L 'ALL_DONE'
