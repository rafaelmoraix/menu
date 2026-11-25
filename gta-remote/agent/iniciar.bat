@echo off
cd /d "%~dp0"
where py >nul 2>nul || (echo ERRO: Python nao encontrado. Instale em python.org marcando "Add to PATH". & pause & exit /b)
if not exist .venv\Scripts\python.exe py -3 -m venv .venv
echo Conferindo dependencias...
.venv\Scripts\python -m pip install -q --disable-pip-version-check -r requirements.txt
if errorlevel 1 (echo ERRO ao instalar dependencias. Tire um print desta janela. & pause & exit /b)
.venv\Scripts\python agent.py
pause
