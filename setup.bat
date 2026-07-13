@echo off
echo ============================================================
echo   INSTALLATION — LOGICIEL DE GESTION PHARMACEUTIQUE
echo   Clinique Tounkara
echo ============================================================
echo.

:: 1. Création de l'environnement virtuel Python
echo [1/4] Creation de l'environnement virtuel...
python -m venv venv
if %errorlevel% neq 0 (
    echo [ERREUR] Impossible de creer l'environnement virtuel. Verifiez que Python est installe.
    pause
    exit /b
)

:: 2. Activation de l'environnement et installation des packages
echo [2/4] Installation des dependances...
call venv\Scripts\activate
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERREUR] Impossible d'installer les dependances.
    pause
    exit /b
)

:: 3. Migrations de base de données
echo [3/4] Initialisation de la base de donnees...
python manage.py makemigrations pharmacie
python manage.py migrate
if %errorlevel% neq 0 (
    echo [ERREUR] Impossible de migrer la base de donnees.
    pause
    exit /b
)

:: 4. Création du compte administrateur
echo [4/4] Creation du compte Administrateur...
echo.
echo Veuillez saisir le nom d'utilisateur, l'email et le mot de passe du compte Admin.
python manage.py createsuperuser

echo.
echo ============================================================
echo   INSTALLATION TERMINEE AVEC SUCCES !
echo   Pour lancer le logiciel, double-cliquez sur "start.bat"
echo ============================================================
echo.
pause
