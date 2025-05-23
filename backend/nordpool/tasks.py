# Importy
from celery import shared_task
from zeep import Client
from zeep.transports import Transport
from requests import Session
from requests.auth import HTTPDigestAuth
from .models import (ServerData, CalculatedResult, SimulatedSolarAndGridPower,
                    SimulatedBattery, OptimizationDecision, PriceArea, ElectricityPrice)
from django.utils import timezone
from django.db.models import Avg
from decimal import Decimal
import logging
import time
import random

# Konfiguracja loggera
logger = logging.getLogger(__name__)

# Konfiguracja
WSDL_URL = 'http://172.16.16.60/EWS/DataExchange.svc?wsdl'
USERNAME = 'kvk'
PASSWORD = 'KvK-DataAccess1'
VALUE_IDS = ["4@1042@V", "7@1042@V", '9@-685@V']


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
def optimize_energy_usage():
    """
    Task that optimizes energy management based on:
    - battery charge level
    - current solar energy production
    - current energy consumption
    - current and forecasted energy prices
    """
    try:
        # 1. Get battery data
        battery = SimulatedBattery.objects.first()
        if not battery:
            logger.error("No battery data in the system")
            return "Error: no battery data"

        # 2. Get current production/consumption data
        power_data = SimulatedSolarAndGridPower.objects.first()
        if not power_data:
            logger.error("No production/consumption data in the system")
            return "Error: no production/consumption data"

        # 3. Calculate energy surplus/deficit
        surplus = float(power_data.solar_power) - float(power_data.usage)

        # 4. Get current energy price (for the first available price area)
        price_area = PriceArea.objects.first()
        if not price_area:
            logger.warning("No price area in the system")
            return "Error: no price areas"

        current_hour = timezone.now().replace(minute=0, second=0, microsecond=0)
        current_price = ElectricityPrice.objects.filter(
            area=price_area,
            timestamp__gte=current_hour,
            timestamp__lt=current_hour + timezone.timedelta(hours=1)
        ).first()

        if not current_price:
            logger.warning("No current energy prices")
            return "Error: no current energy prices"

        # 5. Calculate average price from last 24h for comparison
        last_24h = timezone.now() - timezone.timedelta(hours=24)
        avg_price = ElectricityPrice.objects.filter(
            area=price_area,
            timestamp__gte=last_24h
        ).aggregate(avg=Avg('price'))['avg'] or 0

        # 6. Decision parameters
        battery_charge_percent = (float(battery.current_charge) / float(battery.capacity)) * 100
        price_is_high = float(current_price.price) > float(avg_price) * 1.1  # Price is high when 10% above average

        # 7. Decision logic
        decision = ""
        decision_reason = ""
        battery_level_before = float(battery.current_charge)
        new_charge = float(battery.current_charge)

        if surplus > 0:  # Energy surplus
            # If battery is full, always sell surplus
            if battery_charge_percent >= 99.9:  # Practically 100% (considering precision)
                decision = f"SELL TO GRID: Surplus {surplus:.2f}W, price {current_price.price} {current_price.currency}"
                decision_reason = (f"Battery is fully charged ({battery_charge_percent:.2f}%), "
                                  f"so we're selling all surplus regardless of price ({current_price.price}).")
                logger.info(f"Decision: {decision}")
            elif battery_charge_percent >= 80 and price_is_high:
                # Sell surplus to the grid when price is high
                decision = f"SELL TO GRID: Surplus {surplus:.2f}W, price {current_price.price} {current_price.currency}"
                decision_reason = (f"Battery charged to {battery_charge_percent:.2f}% (above 80%), "
                                  f"and current price ({current_price.price}) is high "
                                  f"(above average {avg_price:.2f}), so we're selling the surplus.")
                logger.info(f"Decision: {decision}")
            else:
                # Charge battery with surplus
                energy_to_charge = min(surplus, float(battery.capacity) - float(battery.current_charge))
                new_charge += energy_to_charge
                decision = f"CHARGE BATTERY: {energy_to_charge:.2f}W from surplus {surplus:.2f}W"
                if battery_charge_percent >= 80:
                    decision_reason = (f"Battery charged to {battery_charge_percent:.2f}%, but current price "
                                      f"({current_price.price}) is not high enough (average: {avg_price:.2f}).")
                else:
                    decision_reason = (f"Battery charged only to {battery_charge_percent:.2f}% (below 80%), "
                                      f"so charging the battery is a priority.")
                logger.info(f"Decision: {decision}")
        else:  # Energy deficit
            if battery_charge_percent > 20 and price_is_high:
                # Discharge battery when price is HIGH
                energy_from_battery = min(abs(surplus), float(battery.current_charge) - float(battery.capacity) * 0.2)
                new_charge -= energy_from_battery
                decision = f"DISCHARGE BATTERY: {energy_from_battery:.2f}W to cover deficit {abs(surplus):.2f}W"
                decision_reason = (f"Battery charged to {battery_charge_percent:.2f}% (above 20%), "
                                  f"and current price ({current_price.price}) is high "
                                  f"(above average {avg_price:.2f}), so we're using battery energy.")
                logger.info(f"Decision: {decision}")
            else:
                # Get energy from grid
                decision = f"DRAW FROM GRID: {abs(surplus):.2f}W, price {current_price.price} {current_price.currency}"
                if battery_charge_percent <= 20:
                    decision_reason = (f"Battery charged only to {battery_charge_percent:.2f}% (below 20%), "
                                      f"so we're protecting remaining battery energy.")
                else:
                    decision_reason = (f"Current price ({current_price.price}) is low "
                                      f"(below average {avg_price:.2f}), so it's cost-effective to buy from the grid.")
                logger.info(f"Decision: {decision}")

        # 8. Update battery state
        battery.current_charge = Decimal(str(new_charge))
        battery.save()

        # 9. Save decision history
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

        return f"Energy usage optimized: {decision}"

    except Exception as e:
        msg = f"Error during energy management optimization: {str(e)}"
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


@shared_task
def simulate_solar_and_grid_power():
    """Generowanie realistycznych danych o produkcji solarnej i zużyciu energii"""
    try:
        logger.info("Generowanie danych o produkcji i zużyciu energii")

        # Określ aktualną godzinę dnia dla realistycznej produkcji solarnej
        current_hour = timezone.now().hour - 2

        # Maksymalna możliwa moc instalacji solarnej (W)
        max_solar_capacity = 5000.0

        # Profil produkcji solarnej w zależności od pory dnia (0-1 jako % maksymalnej mocy)
        solar_profile = {
            0: 0.00, 1: 0.00, 2: 0.00, 3: 0.00, 4: 0.00, 5: 0.02,
            6: 0.10, 7: 0.25, 8: 0.45, 9: 0.65, 10: 0.80, 11: 0.93,
            12: 0.98, 13: 0.95, 14: 0.85, 15: 0.70, 16: 0.55, 17: 0.35,
            18: 0.15, 19: 0.05, 20: 0.00, 21: 0.00, 22: 0.00, 23: 0.00
        }

        # Współczynnik dla aktualnej godziny z niewielką losową wariancją
        solar_factor = solar_profile.get(current_hour, 0.0)
        solar_factor *= (1 + random.uniform(-0.2, 0.1))  # Dodaj losową zmienność (-20% do +10%)

        # Oblicz produkcję solarną
        solar_power = max_solar_capacity * solar_factor

        # Symuluj zużycie energii (podstawowe + zmienne)
        base_usage = 1100.0  # Stałe zużycie bazowe (W)

        # Profil zużycia w zależności od pory dnia (współczynnik)
        usage_profile = {
            0: 0.6, 1: 0.5, 2: 0.5, 3: 0.5, 4: 0.5, 5: 0.6,
            6: 0.8, 7: 1.1, 8: 1.3, 9: 1.2, 10: 1.1, 11: 1.0,
            12: 1.0, 13: 1.0, 14: 1.0, 15: 1.1, 16: 1.2, 17: 1.4,
            18: 1.6, 19: 1.7, 20: 1.5, 21: 1.3, 22: 1.0, 23: 0.8
        }

        usage_factor = usage_profile.get(current_hour, 1.0)
        usage_factor *= (1 + random.uniform(-0.1, 0.1))  # Dodaj losową zmienność (-10% do +10%)

        # Oblicz zużycie energii
        usage = base_usage * usage_factor

        # Oblicz bilans mocy (dodatni: nadwyżka, ujemny: deficyt)
        power_balance = solar_power - usage

        # Zależnie od bilansu, określ moc pobieraną/oddawaną do sieci
        if power_balance >= 0:
            # Nadwyżka - możemy oddawać do sieci
            grid_power = -power_balance  # Wartość ujemna oznacza oddawanie do sieci
        else:
            # Deficyt - musimy pobierać z sieci
            grid_power = -power_balance  # Wartość dodatnia oznacza pobór z sieci

        # Zapisz lub zaktualizuj dane w bazie
        power_data, created = SimulatedSolarAndGridPower.objects.update_or_create(
            id=1,
            defaults={
                'solar_power': round(Decimal(str(solar_power)), 2),
                'grid_power': round(Decimal(str(grid_power)), 2),
                'usage': round(Decimal(str(usage)), 2),
                'timestamp': timezone.now()
            }
        )

        logger.info(f"Wygenerowano dane: Solar={power_data.solar_power}W, "
                    f"Grid={power_data.grid_power}W, Usage={power_data.usage}W")

        return f"Wygenerowano dane o produkcji i zużyciu energii: Solar={power_data.solar_power}W"

    except Exception as e:
        msg = f"Błąd podczas symulacji mocy: {str(e)}"
        logger.error(msg, exc_info=True)
        return msg