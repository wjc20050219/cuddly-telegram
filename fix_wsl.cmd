@echo off
chcp 65001 >nul
title 修复 WSL 服务 - RiceVar-ID
echo ============================================================
echo    RiceVar-ID  -  WSL 服务修复工具
echo ============================================================
echo.

:: 检查是否已有管理员权限
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo  [1/2] 需要管理员权限，正在请求提权...
    echo        请在弹出窗口点击 [ 是 ]
    echo.
    powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

echo  [1/2] 已获得管理员权限
echo.
echo  [2/2] 开始修复 WSL 服务...
echo        整个过程约 30-60 秒，请不要关闭窗口
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "D:\dsh\RiceVar-ID\recover_wsl2.ps1"

echo.
echo ============================================================
echo   修复流程已结束
echo ============================================================
echo.
echo   详细日志: D:\dsh\RiceVar-ID\wsl_recovery.log
echo.
echo   接下来可以回到对话里告诉我"好了"，
echo   我会自动验证 WSL 是否恢复正常。
echo.
pause
