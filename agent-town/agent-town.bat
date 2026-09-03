@echo off
rem Agent Town - 3D world of your agents, driven live by the Pixel Agents office feed.
rem Portable: runs from wherever this folder lives. Needs Node (npx) + Python 3 on PATH.
cd /d "%~dp0"
netstat -ano | findstr ":5177" | findstr LISTENING >nul || (start "Pixel Agents" /min cmd /c "npx -y pixel-agents --port 5177" & timeout /t 6 /nobreak >nul)
netstat -ano | findstr ":5180" | findstr LISTENING >nul || start "Agent Town server" /min cmd /c "python serve.py"
timeout /t 2 /nobreak >nul
start "" "http://127.0.0.1:5180/"
