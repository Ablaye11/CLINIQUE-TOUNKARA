# Clinique Tounkara

Application Django de gestion pharmaceutique.

## Installation locale

1. Clone le dépôt:

```bash
git clone https://github.com/Ablaye11/CLINIQUE-TOUNKARA.git
cd CLINIQUE-TOUNKARA
```

2. Crée un environnement virtuel:

```bash
python -m venv venv
source venv/bin/activate   # sur Linux/Mac
venv\Scripts\activate      # sur Windows
pip install --upgrade pip
pip install -r requirements.txt
```

3. Crée un fichier `.env` à partir de l'exemple:

```bash
copy .env.example .env
```

4. Modifie `.env` si nécessaire. Par défaut, l'application démarrera en mode développement.

5. Applique les migrations:

```bash
python manage.py migrate
```

6. Lance le serveur local:

```bash
python manage.py runserver
```

## Déploiement sur PythonAnywhere

1. Clone le dépôt sur PythonAnywhere:

```bash
cd ~
git clone https://github.com/Ablaye11/CLINIQUE-TOUNKARA.git
cd CLINIQUE-TOUNKARA
```

2. Crée le virtualenv et installe les dépendances:

```bash
python3.13 -m venv ~/venv
source ~/venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

3. Dans l'onglet `Web` de PythonAnywhere, configure les variables d'environnement:

- `DJANGO_SECRET_KEY` : clé secrète réelle
- `DJANGO_DEBUG` : `False`
- `DJANGO_ALLOWED_HOSTS` : `CLINIQUETOUNKARA.pythonanywhere.com`
- `DJANGO_CSRF_TRUSTED_ORIGINS` : `https://CLINIQUETOUNKARA.pythonanywhere.com`
- `DJANGO_CORS_ALLOW_ALL_ORIGINS` : `False`

4. Configure le fichier WSGI PythonAnywhere:

```python
import os
import sys

path = '/home/CLINIQUETOUNKARA/CLINIQUE-TOUNKARA'
if path not in sys.path:
    sys.path.insert(0, path)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharma_project.settings')

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

5. Exécute les migrations :

```bash
source ~/venv/bin/activate
cd ~/CLINIQUE-TOUNKARA
python manage.py migrate
```

6. Collecte les fichiers statiques:

```bash
python manage.py collectstatic --noinput
```

7. Recharge l'application dans l'onglet `Web`.

## Notes

- Ne versionne pas le fichier `.env` dans Git.
- En production, `DEBUG` doit être `False`.
- Ne publie jamais `DJANGO_SECRET_KEY` en clair sur GitHub.
