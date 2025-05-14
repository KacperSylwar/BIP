FROM python:3.10-slim

WORKDIR /app

# Instalacja potrzebnych pakietów
RUN pip install poetry
RUN apt-get update && apt-get install -y --no-install-recommends gcc python3-dev libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Kopiowanie plików konfiguracyjnych
COPY pyproject.toml poetry.lock* ./

# Aby naprawić błąd instalacji
RUN touch README.md

# Konfiguracja Poetry, aby nie używał wirtualnego środowiska i nie instalował bieżącego projektu
RUN poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi --no-root

# Kopiowanie kodu aplikacji
COPY . .

# Skrypt startowy
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]

# Domyślne polecenie
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]