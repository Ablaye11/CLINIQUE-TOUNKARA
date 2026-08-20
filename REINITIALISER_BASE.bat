@echo off
chcp 65001 >nul
title Remise à Zéro de la Base — Clinique Tounkara
color 0C

echo.
echo  ╔══════════════════════════════════════════════════════════╗
echo  ║  ⚠️   REMISE À ZÉRO DE LA BASE DE DONNÉES               ║
echo  ║       Effacement des données de test avant livraison     ║
echo  ╚══════════════════════════════════════════════════════════╝
echo.
echo  Cette action va SUPPRIMER TOUS les médicaments, ventes,
echo  mouvements de stock et fournisseurs de test.
echo.
echo  Vos comptes utilisateurs (Admin / Caissiers) SERONT CONSERVÉS.
echo.
set /p CONFIRM="Voulez-vous vraiment continuer ? (O/N) : "

if /i "%CONFIRM%"=="O" (
    echo.
    echo  Activation de l'environnement virtuel...
    call venv\Scripts\activate.bat
    
    echo  Effacement des données...
    python -c "import os, django; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharma_project.settings'); django.setup(); from pharmacie.models import Medicament, Vente, LigneVente, MouvementStock, Fournisseur; LigneVente.objects.all().delete(); Vente.objects.all().delete(); MouvementStock.objects.all().delete(); Medicament.objects.all().delete(); Fournisseur.objects.all().delete(); print('✅ Base de données remise à zéro avec succès !')"
    echo.
    echo  ╔══════════════════════════════════════════════════════════╗
    echo  ║  ✅  LA BASE EST DÉSORMAIS 100%% PROPRE POUR LE CLIENT   ║
    echo  ╚══════════════════════════════════════════════════════════╝
) else (
    echo.
    echo  Opération annulée.
)

echo.
pause
