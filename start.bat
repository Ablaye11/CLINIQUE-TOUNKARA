@echo off
chcp 65001 >nul
title 🏥 Clinique Tounkara — Démarrage Serveur Pharmacie
color 0A

echo.
echo  ╔══════════════════════════════════════════════════════╗
echo  ║     CLINIQUE TOUNKARA — LOGICIEL PHARMACIE           ║
echo  ║           Démarrage du Serveur Local                 ║
echo  ╚══════════════════════════════════════════════════════╝
echo.

:: Récupérer l'adresse IP locale (première IPv4 trouvée)
for /f "tokens=2 delims=:" %%i in ('ipconfig ^| findstr /i "IPv4"') do (
    set LOCAL_IP=%%i
    goto :found_ip
)
:found_ip
set LOCAL_IP=%LOCAL_IP:~1%
if "%LOCAL_IP%"=="" set LOCAL_IP=localhost

echo  Activation de l'environnement virtuel...
call venv\Scripts\activate.bat

echo  Vérification de la base de données...
python manage.py migrate --run-syncdb 2>nul

echo.
echo  ╔══════════════════════════════════════════════════════╗
echo  ║  ✅  SERVEUR DÉMARRÉ — PRÊT POUR LE RÉSEAU LOCAL    ║
echo  ║                                                      ║
echo  ║  📌  Sur CE poste (serveur) :                        ║
echo  ║      http://127.0.0.1:8000                           ║
echo  ║                                                      ║
echo  ║  📡  Depuis les AUTRES POSTES (réseau local) :       ║
echo  ║      http://%LOCAL_IP%:8000                   ║
echo  ║                                                      ║
echo  ║  ⚠️  Ne PAS fermer cette fenêtre tant que           ║
echo  ║     le logiciel est utilisé !                        ║
echo  ╚══════════════════════════════════════════════════════╝
echo.

:: Démarrer le serveur sur toutes les interfaces réseau (0.0.0.0 = accessible depuis tout le LAN)
python manage.py runserver 0.0.0.0:8000

echo.
echo  Le serveur a été arrêté.
pause
