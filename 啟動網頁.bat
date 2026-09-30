@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 正在啟動台灣氣象互動儀表板，請稍候...
python -m streamlit run app.py
pause
