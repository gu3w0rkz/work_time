#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt
cd api
python manage.py collectstatic --no-input --clear --verbosity 1
echo "==> Static files collected: $(find staticfiles -type f 2>/dev/null | wc -l) files"
python manage.py migrate
