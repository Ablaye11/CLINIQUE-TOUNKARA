@echo off
title Clinique Tounkara - Pharma Server
echo ============================================================
echo   DEMARRAGE — LOGICIEL DE GESTION PHARMACEUTIQUE
echo   Clinique Tounkara
echo ============================================================
echo.

:: Récupération de l'adresse IP locale pour l'accès multi-postes
echo Recherche de votre adresse IP locale en cours...
for /f "tokens=2 delims=:" %%i in ('ipconfig ^| findstr /i "IPv4"') do (
    set LOCAL_IP=%%i
    goto :found_ip
)
:found_ip
:: Supprimer l'espace de début si présent
set LOCAL_IP=%LOCAL_IP:~1%

if "%LOCAL_IP%"=="" (
    set LOCAL_IP=localhost
)

echo.
echo ============================================================
echo   SERVEUR DISPONIBLE !
echo.
echo   - Sur cet ordinateur :  http://127.0.0.1:8000
echo   - Depuis le reseau :     http://%LOCAL_IP%:8000
echo ============================================================
echo.

:: Activation de l'environnement virtuel et démarrage du serveur
call venv\Scripts\activate
python manage.py runserver 0.0.0.0:8000
pause
