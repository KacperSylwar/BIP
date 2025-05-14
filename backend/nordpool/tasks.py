from celery import shared_task
from zeep import Client
from zeep.transports import Transport
from requests import Session
from requests.auth import HTTPDigestAuth
from .models import ServerData
from django.utils import timezone

# Konfiguracja
WSDL_URL = 'http://172.16.16.60/EWS/DataExchange.svc?wsdl'
USERNAME = 'kvk'
PASSWORD = 'KvK-DataAccess1'
VALUE_IDS = ["4@1042@V", "4@1731@V", "4@1601@V"]


@shared_task
def fetch_server_data():
    """Zadanie pobierające dane z serwera SOAP i zapisujące je do bazy danych"""
    # Konfiguracja sesji z uwierzytelnianiem Digest
    session = Session()
    session.auth = HTTPDigestAuth(USERNAME, PASSWORD)

    # Utworzenie klienta SOAP
    client = Client(wsdl=WSDL_URL, transport=Transport(session=session))

    results = []
    for value_id in VALUE_IDS:
        try:
            request_data = {
                'GetValuesIds': [value_id],
                'version': "1.0"
            }

            response = client.service.GetValues(**request_data)
            value_items = response.GetValuesItems.ValueItem

            if value_items:
                for item in value_items:
                    # Zapisz do bazy danych
                    server_data, created = ServerData.objects.update_or_create(
                        server_id=item.Id,
                        defaults={'value': item.Value}
                    )
                    results.append(f"ID={item.Id}, State={item.State}, Value={item.Value}")
            else:
                results.append(f"⚠️ No value returned for ID: {value_id}")

        except Exception as e:
            results.append(f"❌ Error for ID {value_id}: {str(e)}")

    return "\n".join(results)