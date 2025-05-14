#!/bin/bash

# Wykonanie migracji
echo "Wykonywanie migracji bazy danych..."
python manage.py migrate

# Uruchomienie polecenia z CMD
exec "$@"