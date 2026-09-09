@echo off
chcp 65001 >nul
cd /d "%~dp0"
"C:\Users\shenyf\AppData\Local\Programs\Python\Python314\pythonw.exe" tools\publish_to_github.py 2>"%~dp0tools\publish_error.log"
if %errorlevel% neq 0 (
    echo GUI 启动失败，错误日志见 tools\publish_error.log：
    type "%~dp0tools\publish_error.log"
    pause
)
