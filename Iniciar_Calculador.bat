@echo off
title Calculador EPS - Covintec
color 0A
cls
echo.
echo ========================================
echo   CALCULADOR DE RENDIMIENTO EPS
echo   Covintec - Produccion
echo ========================================
echo.
echo [OK] Iniciando servidor web...
echo [OK] El navegador se abrira en 3 segundos
echo [INFO] Para cerrar: presiona Ctrl + C
echo.
echo ========================================
echo.

timeout /t 3 >nul
start http://127.0.0.1:8501

python -m streamlit run app_web_eps.py --server.headless true --server.port 8501 --browser.gatherUsageStats false --server.enableCORS false

pause