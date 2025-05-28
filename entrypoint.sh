#!/bin/bash

# ждем, пока база данных будет готова
echo "Waiting for database..."
sleep 5

# создаем миграции
echo "Creating migrations..."
python manage.py makemigrations

# применяем миграции
echo "Applying migrations..."
python manage.py migrate

# делаем статику
python manage.py collectstatic --noinput

# запускаем Django
echo "Starting Django server..."
uvicorn shop_test.asgi:application --host 0.0.0.0 --port 8000 --reload