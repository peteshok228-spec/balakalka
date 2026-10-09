@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist .venv (
    echo Первый запуск: создаю окружение и ставлю зависимости...
    python -m venv .venv || (echo Установите Python 3.10+ с python.org & pause & exit /b 1)
    .venv\Scripts\python -m pip install --upgrade pip
    .venv\Scripts\python -m pip install -r requirements.txt
)
.venv\Scripts\python -m balakalka
pause
