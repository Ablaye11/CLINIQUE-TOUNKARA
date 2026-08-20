# Guide de Déploiement — Clinique Tounkara Pharmacie

## Architecture

Un seul PC fait office de serveur. Les autres postes se connectent via le navigateur web. La base de données est centralisée sur le serveur et partagée automatiquement.

## Étapes

### 1. Sur le PC Serveur

1. Installer Python 3.10+ depuis https://python.org (cocher "Add to PATH")
2. Double-cliquer sur `installer.bat`
3. Suivre les instructions pour créer le compte administrateur

### 2. Démarrage quotidien

Double-cliquer sur `start.bat`. L'adresse réseau s'affiche (ex: 192.168.1.10:8000).

### 3. Connexion depuis les autres postes

Ouvrir Chrome/Firefox et taper : http://[IP affichée]:8000

### 4. Pare-feu Windows

Si les autres postes ne se connectent pas : Pare-feu Windows > Règles entrantes > Nouveau > Port 8000 > Autoriser.
