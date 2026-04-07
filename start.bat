@echo off
chcp 65001 >nul
echo.
echo ╔═══════════════════════════════════════════════════════╗
echo ║     🤖 AI Learning - 智能句子结构学习系统              ║
echo ║     支持英语、汉语双语言 · 智能分析 · 个性化练习        ║
echo ╚═══════════════════════════════════════════════════════╝
echo.
echo 启动方式:
echo   [1] 命令行界面 (CLI)
echo   [2] Web 界面 (浏览器)
echo   [3] 退出
echo.

set /p choice=请选择 (1-3): 

if "%choice%"=="1" goto cli
if "%choice%"=="2" goto web
if "%choice%"=="3" goto exit

echo 无效选择，默认启动 CLI
goto cli

:cli
echo.
echo 正在启动 CLI 模式...
cd /d "C:\Users\27977\.qclaw\workspace\ai-learning"
python cli.py
pause
goto end

:web
echo.
echo 正在启动 Web 服务...
echo 请在浏览器中访问: http://localhost:7861
cd /d "C:\Users\27977\.qclaw\workspace\ai-learning"
python web.py
pause
goto end

:exit
echo 再见!

:end
