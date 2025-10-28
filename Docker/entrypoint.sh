#!/bin/sh

echo "Waiting for the database to be ready..."

while ! nc -z db 5432; do
  sleep 1
done

echo "Database started!"

python manage.py migrate
python manage.py collectstatic --noinput
python manage.py runserver 0.0.0.0:8000
