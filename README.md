# BIP
https://drive.google.com/drive/folders/1xdHsuUFHPPYn_TT4uY2f-lZW0b2KxaI5



(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -


"""
import time
from zeep import Client
from zeep.transports import Transport
from requests import Session
from requests.auth import HTTPDigestAuth

# Konfiguracja SOAP Clienta
WSDL_URL = 'http://172.30.10.11/EWS/DataExchange.svc?wsdl'
USERNAME = 'kvk'
PASSWORD = 'KvK-DataAccess1'

session = Session()
session.auth = HTTPDigestAuth(USERNAME, PASSWORD)

client = Client(wsdl=WSDL_URL, transport=Transport(session=session))

def get_values():
    try:
        # Tworzymy request dokładnie taki jak w C#
        request_data = {
            'GetValuesIds': ["4@1042@V", "6@1042@V", "7@1042@V", "8@1042@V"],
            'version': "1.0"
        }

        response = client.service.GetValues(**request_data)

        if response.GetValuesItems:
            for idx, value_item in enumerate(response.GetValuesItems, start=1):
                print(f"Value {idx}: {value_item.Value}")
        else:
            print("No values returned.")

    except Exception as e:
        print(f"Error: {e}")

def main():
    while True:
        get_values()
        print("Waiting 10 seconds...\n")
        time.sleep(10)  # zamiast Timer: co 10 sekund

if __name__ == "__main__":
    main()
"""
