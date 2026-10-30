@echo off
rem Mở app 字引 (Jibiki): chạy server trên máy và mở trình duyệt tại http://localhost:8780
cd /d "%~dp0"
py -3 server.py
if errorlevel 1 python server.py
pause
