@echo off
cd /d "%~dp0"
set PYW=C:\Users\shenyf\AppData\Local\Programs\Python\Python314\pythonw.exe
"%PYW%" tools\publish_to_github.py 2>"tools\publish_error.log"
if errorlevel 1 (
    echo [ERROR] GUI failed to start. Log: tools\publish_error.log
    type "tools\publish_error.log"
    pause
)
