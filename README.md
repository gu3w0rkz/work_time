# WorkTime (minimal)

Progetto minimo Django per tracciamento tempo.

Istruzioni rapide:

1. Crea un virtualenv e installa dipendenze:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Applica migrazioni e crea superuser:

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
```

Per accedere: usa l'email come username sulla pagina di login (`/login/`).
