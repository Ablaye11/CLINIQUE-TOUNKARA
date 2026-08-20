@echo off
chcp 65001 >nul
title Sauvegarde Base de Données — Clinique Tounkara
color 0B

echo.
echo  ╔═══════════════════════════════════════════════════╗
echo  ║  💾  SAUVEGARDE DE LA BASE DE DONNÉES             ║
echo  ╚═══════════════════════════════════════════════════╝
echo.

:: Créer le dossier de sauvegarde s'il n'existe pas
if not exist "sauvegardes" mkdir sauvegardes

:: Nom du fichier avec date et heure
for /f "tokens=1-3 delims=/ " %%a in ("%date%") do set DATE_FMT=%%c-%%b-%%a
for /f "tokens=1-2 delims=:." %%a in ("%time%") do set HEURE=%%a%%b

:: Supprimer les espaces éventuels
set DATE_FMT=%DATE_FMT: =%
set HEURE=%HEURE: =0%

set BACKUP_FILE=sauvegardes\pharmacie_db_%DATE_FMT%_%HEURE%.sqlite3

copy pharmacie_db.sqlite3 "%BACKUP_FILE%"

echo.
echo  ✅ Sauvegarde réussie !
echo  📁 Fichier : %BACKUP_FILE%
echo.

:: Garder seulement les 10 dernières sauvegardes (optionnel)
echo  Nettoyage des anciennes sauvegardes (garde les 10 dernières)...
pushd sauvegardes
for /f "skip=10 delims=" %%f in ('dir /b /o-d *.sqlite3 2^>nul') do del "%%f"
popd

echo  Terminé !
pause
