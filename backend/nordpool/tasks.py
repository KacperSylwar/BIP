from celery import shared_task
from zeep import Client
from zeep.transports import Transport
from requests import Session
from requests.auth import HTTPDigestAuth
from .models import ServerData, CalculatedResult,SimulatedSolarAndGridPower, SimulatedBattery, OptimizationDecision
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
VALUE_IDS = ["4@1042@V", "7@1042@V",'9@-685@V']


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


@shared_task
def simulate_solar_and_grid_power():
    """
    Zadanie symulujące produkcję energii z paneli solarnych oraz pobór z sieci.
    Wartości zmieniają się w sposób realistyczny, uwzględniając porę dnia.
    """
    logger.info("Rozpoczynam symulację mocy paneli solarnych i poboru z sieci")

    try:
        # Pobierz aktualny czas, aby symulować zależność od pory dnia
        current_time = timezone.now()
        hour = current_time.hour

        # Symulacja mocy paneli solarnych (dzień/noc)
        if 6 <= hour < 22:  # Dzień
            # Symulacja krzywej dziennej (wyższa w środku dnia)
            hour_factor = 1.0 - abs(hour - 14) / 8.0  # Szczyt o 14:00
            base_solar = 2000 * hour_factor  # Maksymalna moc 2000W
            solar_power = base_solar * (1 + random.uniform(-0.1, 0.1))
        else:  # Noc
            solar_power = random.uniform(0, 10)  # W nocy minimalna moc

        # Symulacja zużycia energii (usage)
        base_usage = 1200  # Podstawowe zużycie 1000W

        if 6 <= hour < 9 or 18 <= hour < 23:  # Rano lub wieczór
            usage_factor = 1.5  # Zwiększone zużycie
        elif 23 <= hour or hour < 6:  # Noc
            usage_factor = 0.5  # Zmniejszone zużycie
        else:  # Dzień
            usage_factor = 1.0  # Normalne zużycie

        usage = base_usage * usage_factor * (1 + random.uniform(-0.2, 0.2))

        # Obliczenie poboru z sieci
        grid_power = max(0, usage - solar_power)

        # Zapisz lub zaktualizuj dane
        power_data, created = SimulatedSolarAndGridPower.objects.get_or_create(
            pk=1,  # Zawsze używamy tego samego rekordu
            defaults={
                'solar_power': solar_power,
                'grid_power': grid_power,
                'usage': usage
            }
        )

        if not created:
            power_data.solar_power = solar_power
            power_data.grid_power = grid_power
            power_data.usage = usage
            power_data.save()

        logger.info(f"Symulacja zakończona: Solar={solar_power:.2f}W, Grid={grid_power:.2f}W, Usage={usage:.2f}W")
        return "Zaktualizowano dane symulacji mocy"

    except Exception as e:
        msg = f"Błąd podczas symulacji mocy: {str(e)}"
        logger.error(msg, exc_info=True)
        return msg


from celery import shared_task
from django.utils import timezone
from django.db.models import Avg
from decimal import Decimal
import logging
from .models import SimulatedBattery, SimulatedSolarAndGridPower, ElectricityPrice, PriceArea

logger = logging.getLogger(__name__)


@shared_task
def optimize_energy_usage():
    """
    Zadanie optymalizujące zarządzanie energią w zależności od:
    - stopnia naładowania baterii
    - aktualnej produkcji energii solarnej
    - bieżącego zużycia energii
    - aktualnych i przewidywanych cen energii
    """
    try:
        # 1. Pobierz dane o baterii
        battery = SimulatedBattery.objects.first()
        if not battery:
            logger.error("Brak danych o baterii w systemie")
            return "Błąd: brak danych o baterii"

        # 2. Pobierz aktualne dane o produkcji/zużyciu
        power_data = SimulatedSolarAndGridPower.objects.first()
        if not power_data:
            logger.error("Brak danych o produkcji/zużyciu w systemie")
            return "Błąd: brak danych o produkcji/zużyciu"

        # 3. Oblicz nadwyżkę/deficyt energii
        surplus = float(power_data.solar_power) - float(power_data.usage)

        # 4. Pobierz aktualną cenę energii (dla pierwszego dostępnego obszaru cenowego)
        price_area = PriceArea.objects.first()
        if not price_area:
            logger.warning("Brak obszaru cenowego w systemie")
            return "Błąd: brak obszarów cenowych"

        current_hour = timezone.now().replace(minute=0, second=0, microsecond=0)
        current_price = ElectricityPrice.objects.filter(
            area=price_area,
            timestamp__gte=current_hour,
            timestamp__lt=current_hour + timezone.timedelta(hours=1)
        ).first()

        if not current_price:
            logger.warning("Brak aktualnych cen energii")
            return "Błąd: brak aktualnych cen energii"

        # 5. Wylicz średnią cenę z ostatnich 24h dla porównania
        last_24h = timezone.now() - timezone.timedelta(hours=24)
        avg_price = ElectricityPrice.objects.filter(
            area=price_area,
            timestamp__gte=last_24h
        ).aggregate(avg=Avg('price'))['avg'] or 0

        # 6. Parametry decyzyjne
        battery_charge_percent = (float(battery.current_charge) / float(battery.capacity)) * 100
        price_is_good = float(current_price.price) > float(avg_price) * 1.1  # 10% powyżej średniej

        # 7. Logika podejmowania decyzji
        decision = ""
        decision_reason = ""
        battery_level_before = float(battery.current_charge)
        new_charge = float(battery.current_charge)

        if surplus > 0:  # Nadwyżka energii
            # ZMIANA: Jeśli bateria jest pełna, zawsze sprzedaj nadwyżkę
            if battery_charge_percent >= 99.9:  # Praktycznie 100% (uwzględniając niedokładność)
                decision = f"SPRZEDAŻ DO SIECI: Nadwyżka {surplus:.2f}W, cena {current_price.price} {current_price.currency}"
                decision_reason = (f"Bateria jest w pełni naładowana ({battery_charge_percent:.2f}%), "
                                  f"więc sprzedajemy całą nadwyżkę niezależnie od ceny ({current_price.price}).")
                logger.info(f"Decyzja: {decision}")
            elif battery_charge_percent >= 80 and price_is_good:
                # Sprzedaj nadwyżkę do sieci
                decision = f"SPRZEDAŻ DO SIECI: Nadwyżka {surplus:.2f}W, cena {current_price.price} {current_price.currency}"
                decision_reason = (f"Bateria naładowana w {battery_charge_percent:.2f}% (powyżej 80%), "
                                  f"a aktualna cena ({current_price.price}) jest korzystna "
                                  f"(powyżej średniej {avg_price:.2f}), więc sprzedajemy nadwyżkę.")
                logger.info(f"Decyzja: {decision}")
            else:
                # Ładuj baterię nadwyżką
                energy_to_charge = min(surplus, float(battery.capacity) - float(battery.current_charge))
                new_charge += energy_to_charge
                decision = f"ŁADOWANIE BATERII: {energy_to_charge:.2f}W z nadwyżki {surplus:.2f}W"
                if battery_charge_percent >= 80:
                    decision_reason = (f"Bateria naładowana w {battery_charge_percent:.2f}%, ale aktualna cena "
                                      f"({current_price.price}) nie jest wystarczająco korzystna (średnia: {avg_price:.2f}).")
                else:
                    decision_reason = (f"Bateria naładowana tylko w {battery_charge_percent:.2f}% (poniżej 80%), "
                                      f"więc priorytetem jest ładowanie baterii.")
                logger.info(f"Decyzja: {decision}")
        else:  # Deficyt energii
            if battery_charge_percent > 20 and not price_is_good:
                # Rozładuj baterię aby pokryć deficyt
                energy_from_battery = min(abs(surplus), float(battery.current_charge) - float(battery.capacity) * 0.2)
                new_charge -= energy_from_battery
                decision = f"ROZŁADOWANIE BATERII: {energy_from_battery:.2f}W na pokrycie deficytu {abs(surplus):.2f}W"
                decision_reason = (f"Bateria naładowana w {battery_charge_percent:.2f}% (powyżej 20%), "
                                  f"a aktualna cena ({current_price.price}) jest niekorzystna "
                                  f"(poniżej lub blisko średniej {avg_price:.2f}), więc używamy energii z baterii.")
                logger.info(f"Decyzja: {decision}")
            else:
                # Pobierz energię z sieci
                decision = f"POBÓR Z SIECI: {abs(surplus):.2f}W, cena {current_price.price} {current_price.currency}"
                if battery_charge_percent <= 20:
                    decision_reason = (f"Bateria naładowana tylko w {battery_charge_percent:.2f}% (poniżej 20%), "
                                      f"więc chronimy pozostałą energię w baterii.")
                else:
                    decision_reason = (f"Aktualna cena ({current_price.price}) jest korzystna "
                                      f"(powyżej średniej {avg_price:.2f}), więc opłaca się kupić z sieci.")
                logger.info(f"Decyzja: {decision}")

        # 8. Aktualizuj stan baterii
        battery.current_charge = Decimal(str(new_charge))
        battery.save()

        # 9. Zapisz historię decyzji
        OptimizationDecision.objects.create(
            battery_level_before=battery_level_before,
            battery_percentage_before=battery_charge_percent,
            battery_level_after=new_charge,
            battery_percentage_after=(new_charge / float(battery.capacity) * 100),
            solar_power=power_data.solar_power,
            grid_power=power_data.grid_power,
            usage=power_data.usage,
            surplus=surplus,
            current_price=current_price.price,
            avg_price=avg_price,
            decision=decision,
            decision_reason=decision_reason
        )

        return f"Zoptymalizowano użycie energii: {decision}"

    except Exception as e:
        msg = f"Błąd podczas optymalizacji zarządzania energią: {str(e)}"
        logger.error(msg, exc_info=True)
        return msg

@shared_task
def generate_electricity_prices():
    """
    Zadanie generujące realistyczne ceny energii dla obszarów cenowych.
    Generuje dane dla bieżącej godziny i kilku kolejnych.
    """
    logger.info("Rozpoczynam generowanie cen energii")

    try:
        # 1. Sprawdź czy istnieją obszary cenowe, jeśli nie - utwórz domyślne
        if PriceArea.objects.count() == 0:
            logger.info("Tworzę domyślne obszary cenowe")
            default_areas = [
                {"code": "PL", "name": "Polska", "country": "Polska"},
                {"code": "DE", "name": "Niemcy", "country": "Niemcy"},
                {"code": "SE4", "name": "Szwecja (Południe)", "country": "Szwecja"}
            ]
            for area_data in default_areas:
                PriceArea.objects.create(**area_data)

        # 2. Pobierz wszystkie obszary
        price_areas = PriceArea.objects.all()

        # 3. Dla każdego obszaru generuj ceny dla bieżącej i przyszłych godzin
        current_hour = timezone.now().replace(minute=0, second=0, microsecond=0)
        hours_to_generate = 24  # Generuj ceny na 24h do przodu

        for area in price_areas:
            for hour_offset in range(hours_to_generate):
                target_hour = current_hour + timezone.timedelta(hours=hour_offset)

                # Sprawdź czy już istnieją dane dla tej godziny i tego obszaru
                if ElectricityPrice.objects.filter(area=area, timestamp=target_hour).exists():
                    continue

                # Generowanie realistycznej ceny w zależności od pory dnia
                hour = target_hour.hour

                # Bazowa cena (EUR/MWh)
                base_price = 50.0

                # Modyfikatory ceny w zależności od pory dnia
                if 7 <= hour < 10:  # Poranny szczyt
                    price_factor = 1.4
                elif 17 <= hour < 22:  # Wieczorny szczyt
                    price_factor = 1.6
                elif 22 <= hour or hour < 6:  # Noc
                    price_factor = 0.7
                else:  # Pozostałe godziny
                    price_factor = 1.0

                # Dodaj niewielką losową wariację
                price_factor *= (1 + random.uniform(-0.15, 0.15))

                # Różnicuj ceny między obszarami
                if area.code == "DE":
                    area_factor = 0.9  # Nieco tańszy
                elif area.code == "SE4":
                    area_factor = 0.8  # Najtańszy
                else:
                    area_factor = 1.0  # Bazowy

                # Oblicz finalną cenę
                final_price = base_price * price_factor * area_factor

                # Zapisz do bazy
                ElectricityPrice.objects.create(
                    area=area,
                    timestamp=target_hour,
                    price=round(Decimal(str(final_price)), 2),
                    currency="EUR"
                )

            logger.info(f"Wygenerowano ceny dla obszaru {area.code}")

        logger.info(f"Zakończono generowanie cen energii dla {len(price_areas)} obszarów na {hours_to_generate} godzin")
        return "Pomyślnie wygenerowano ceny energii"

    except Exception as e:
        msg = f"Błąd podczas generowania cen energii: {str(e)}"
        logger.error(msg, exc_info=True)
        return msg