@echo off
chcp 65001 >nul
title Installation — Clinique Tounkara Pharmacie
color 0E

echo.
echo  ╔══════════════════════════════════════════════════════════╗
echo  ║  🏥  INSTALLATION CLINIQUE TOUNKARA — PHARMACIE          ║
echo  ║       Première installation sur ce poste serveur         ║
echo  ╚══════════════════════════════════════════════════════════╝
echo.
echo  Ce script va :
echo    1. Créer l'environnement Python virtuel
echo    2. Installer les dépendances
echo    3. Initialiser la base de données
echo    4. Créer le compte Super-Administrateur
echo.
pause

:: Vérifier Python
python --version 2>nul
if errorlevel 1 (
    echo.
    echo  ❌ Python n'est pas installé ou introuvable.
    echo     Téléchargez Python 3.10+ sur https://python.org
    pause
    exit /b 1
)

echo.
echo  ✅ Python détecté.
echo.

:: Créer l'environnement virtuel si absent
if not exist "venv" (
    echo  Création de l'environnement virtuel...
    python -m venv venv
)

echo  Activation de l'environnement...
call venv\Scripts\activate.bat

echo  Installation des dépendances...
pip install -r requirements.txt

echo.
echo  Initialisation de la base de données...
python manage.py migrate

echo.
echo  ╔══════════════════════════════════════════════════════════╗
echo  ║  👤  CRÉATION DU COMPTE SUPER-ADMINISTRATEUR             ║
echo  ╚══════════════════════════════════════════════════════════╝
echo.
echo  Entrez les informations du compte administrateur principal :
echo.
python manage.py createsuperuser

echo.
echo  ╔══════════════════════════════════════════════════════════╗
echo  ║  ✅  INSTALLATION TERMINÉE !                             ║
echo  ║                                                          ║
echo  ║  Lancez le serveur avec : start.bat                      ║
echo  ║  Sauvegardez régulièrement avec : sauvegarder.bat        ║
echo  ╚══════════════════════════════════════════════════════════╝
echo.
pause
