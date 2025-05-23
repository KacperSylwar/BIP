import os
from celery import Celery
from datetime import timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

app = Celery('core')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Używanie adresu Redis z zmiennej środowiskowej lub domyślnego
app.conf.broker_url = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
app.conf.result_backend = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')

@app.task
def fetch_and_calculate():
    """
    Funkcja obsługująca stare zadania zaplanowane w Redis.
    Przekierowuje do nowego zadania fetch_server_data.
    """
    from nordpool.tasks import fetch_server_data
    return fetch_server_data.delay()

# Harmonogram zadań
app.conf.beat_schedule = {
    'simulate-solar-and-grid-power': {
        'task': 'nordpool.tasks.simulate_solar_and_grid_power',
        'schedule': timedelta(seconds=5),
    },
'optimize-energy-usage': {
    'task': 'nordpool.tasks.optimize_energy_usage',
    'schedule': timedelta(seconds=5),  # Uruchamiane co minutę
},
}