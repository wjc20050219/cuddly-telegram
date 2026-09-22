@echo off
chcp 65001 >nul
set LOG=D:\dsh\RiceVar-ID\wsl_install.log
echo ===== STEP1: enable Microsoft-Windows-Subsystem-Linux ===== > "%LOG%"
dism /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart >> "%LOG%" 2>&1
echo EXIT=%errorlevel% >> "%LOG%"
echo ===== STEP2: enable VirtualMachinePlatform ===== >> "%LOG%"
dism /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart >> "%LOG%" 2>&1
echo EXIT=%errorlevel% >> "%LOG%"
echo ===== STEP3: wsl --update ===== >> "%LOG%"
wsl --update >> "%LOG%" 2>&1
echo EXIT=%errorlevel% >> "%LOG%"
if not exist "%LOG%.updated" (
  echo ===== STEP3b: wsl --update --web-download ===== >> "%LOG%"
  wsl --update --web-download >> "%LOG%" 2>&1
  echo EXIT=%errorlevel% >> "%LOG%"
)
echo ===== STEP4: install Ubuntu distro ===== >> "%LOG%"
wsl --install -d Ubuntu --no-launch >> "%LOG%" 2>&1
echo EXIT=%errorlevel% >> "%LOG%"
echo ALL_DONE >> "%LOG%"
