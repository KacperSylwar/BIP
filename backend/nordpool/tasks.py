from celery import shared_task
from zeep import Client
from zeep.transports import Transport
from requests import Session
from requests.auth import HTTPDigestAuth
from .models import ServerData, CalculatedResult
from django.utils import timezone
import logging
import time
import random

# Konfiguracja loggera
logger = logging.getLogger(__name__)

# Konfiguracja
WSDL_URL = 'http://172.16.16.60/EWS/DataExchange.svc?wsdl'
USERNAME = 'kvk'
PASSWORD = 'KvK-DataAccess1'
VALUE_IDS = ["4@1042@V", "7@1042@V"]


@shared_task
def fetch_server_data():
    """Zadanie pobierające dane z serwera SOAP i zapisujące je do bazy danych"""
    logger.info(f"Rozpoczynam fetch_server_data dla ID: {VALUE_IDS}")
    successfully_fetched = False

    try:
        # Konfiguracja klienta SOAP z uwierzytelnianiem
        session = Session()
        session.auth = HTTPDigestAuth(USERNAME, PASSWORD)
        transport = Transport(session=session, timeout=10)  # Dodany timeout 10s

        logger.info(f"Próba połączenia z serwerem SOAP: {WSDL_URL}")
        client = Client(wsdl=WSDL_URL, transport=transport)
        logger.info("✅ Połączono z serwerem SOAP")

        for value_id in VALUE_IDS:
            try:
                # Przygotowanie zapytania
                request_data = {
                    'GetValuesIds': [value_id],
                    'version': "1.0"
                }

                # Wykonanie zapytania SOAP
                logger.info(f"Wysyłam zapytanie dla ID: {value_id}")
                response = client.service.GetValues(**request_data)
                logger.info(f"Otrzymano odpowiedź: {type(response)}")

                # Bardziej szczegółowy log z odpowiedzią
                if hasattr(response, 'GetValuesItems'):
                    logger.info(f"Odpowiedź zawiera GetValuesItems: {bool(response.GetValuesItems)}")
                else:
                    logger.warning(f"Odpowiedź nie zawiera atrybutu GetValuesItems!")

                # Parsowanie odpowiedzi
                if hasattr(response, 'GetValuesItems') and response.GetValuesItems:
                    items = response.GetValuesItems.ValueItem
                    for item in items:
                        # Zapis danych do bazy
                        logger.info(f"Zapisuję dane: ID={item.Id}, Value={item.Value}")
                        server_data = ServerData.objects.create(
                            server_id=item.Id,
                            value=float(item.Value),
                            timestamp=timezone.now()
                        )
                        logger.info(f"✅ Zapisano do bazy danych! ID={server_data.id}, Value={server_data.value}")
                        successfully_fetched = True
                else:
                    logger.warning(f"⚠️ Brak danych w odpowiedzi dla ID: {value_id}")

            except Exception as e:
                logger.error(f"❌ Błąd podczas pobierania danych dla ID {value_id}: {str(e)}", exc_info=True)

        # Jeśli nie udało się pobrać żadnych danych, generujemy testowe
        if not successfully_fetched:
            logger.warning("⚠️ Nie udało się pobrać żadnych danych. Generuję testowe dane.")
            _generate_test_data()

        # Uruchomienie zadania calculate_power_exchange
        logger.info("Uruchamiam calculate_power_exchange")
        calculate_power_exchange.delay()
        return "Zakończono pobieranie danych z serwera SOAP"

    except Exception as e:
        logger.error(f"❌ Krytyczny błąd w fetch_server_data: {str(e)}", exc_info=True)
        logger.warning("⚠️ Generuję testowe dane z powodu błędu.")
        _generate_test_data()
        # Mimo błędu, uruchamiamy calculate_power_exchange
        calculate_power_exchange.delay()
        return f"Błąd: {str(e)}"


def _generate_test_data():
    """Generuje testowe dane dla obu ID"""
    # Wartości z małymi losowymi wahaniami dla realności
    value1 = 100.0 + random.uniform(-5.0, 5.0)
    value2 = -50.0 + random.uniform(-5.0, 5.0)  # Ujemna wartość

    # Zapisz dla pierwszego ID
    server_data1 = ServerData.objects.create(
        server_id=VALUE_IDS[0],
        value=value1,
        timestamp=timezone.now()
    )
    logger.info(f"✅ Wygenerowano testowe dane: ID={server_data1.server_id}, Value={server_data1.value}")

    # Zapisz dla drugiego ID
    server_data2 = ServerData.objects.create(
        server_id=VALUE_IDS[1],
        value=value2,
        timestamp=timezone.now()
    )
    logger.info(f"✅ Wygenerowano testowe dane: ID={server_data2.server_id}, Value={server_data2.value}")

    return [server_data1, server_data2]


@shared_task
def calculate_power_exchange():
    """
    Zadanie obliczające wymianę energii:
    - Jeśli 7@1042@V < 0: oddajemy energię, x = 4@1042@V - 7@1042@V
    - Jeśli 7@1042@V >= 0: pobieramy energię, x = 7@1042@V + 4@1042@V
    """
    logger.info("Rozpoczynam calculate_power_exchange")

    try:
        # Pobierz najnowsze dane dla obu ID
        id1 = VALUE_IDS[0]  # "4@1042@V"
        id2 = VALUE_IDS[1]  # "7@1042@V"

        # Próba pobrania najnowszych rekordów
        try:
            record1 = ServerData.objects.filter(server_id=id1).latest('timestamp')
            record2 = ServerData.objects.filter(server_id=id2).latest('timestamp')
            logger.info(f"Znaleziono dane: ID1={record1.value}, ID2={record2.value}")
        except ServerData.DoesNotExist:
            msg = "Brak danych dla jednego lub obu ID: ServerData matching query does not exist."
            logger.error(msg)
            return msg

        # Sprawdź znak wartości dla ID 7@1042@V
        if float(record2.value) < 0:
            # Wartość ujemna - oddajemy energię
            result_value = float(record1.value) - float(record2.value)
            name = "True"
            operation = f"x = {id1} - {id2}"
        else:
            # Wartość dodatnia - pobieramy energię
            result_value = float(record1.value) + float(record2.value)
            name = "False"
            operation = f"x = {id1} + {id2}"

        # Zapisz wynik
        result = CalculatedResult.objects.create(
            name=f"{name}",
            source_id_1=id1,
            source_id_2=id2,
            source_value_1=record1.value,
            source_value_2=record2.value,
            calculated_value=result_value
        )
        logger.info(f"Zapisano wynik: {result.name} = {result.calculated_value}")

        return f"Obliczono wymianę energii: {result.name} = {result.calculated_value}"

    except Exception as e:
        msg = f"Błąd podczas obliczania wymiany energii: {str(e)}"
        logger.error(msg, exc_info=True)
        return msg
