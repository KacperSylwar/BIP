from django.db import models
from django.utils import timezone


class PriceArea(models.Model):
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=100)
    country = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.name} ({self.code})"


class ElectricityPrice(models.Model):
    area = models.ForeignKey(PriceArea, on_delete=models.CASCADE, related_name='prices')
    timestamp = models.DateTimeField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="EUR")

    class Meta:
        unique_together = ['area', 'timestamp']
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.area.code} - {self.timestamp}: {self.price} {self.currency}"


class ServerData(models.Model):
    server_id = models.CharField(max_length=20, verbose_name="ID")
    value = models.DecimalField(max_digits=20, decimal_places=12)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = "Dane z serwera"
        verbose_name_plural = "Dane z serwera"

    def __str__(self):
        return f"ID: {self.server_id} - Wartość: {self.value}"


class CalculatedResult(models.Model):
    # Nazwa obliczenia
    name = models.CharField(max_length=100)

    # Identyfikatory źródłowych danych
    source_id_1 = models.CharField(max_length=20)
    source_id_2 = models.CharField(max_length=20)

    # Wartości źródłowe
    source_value_1 = models.DecimalField(max_digits=20, decimal_places=12)
    source_value_2 = models.DecimalField(max_digits=20, decimal_places=12)

    # Obliczona wartość
    calculated_value = models.DecimalField(max_digits=20, decimal_places=12)

    # Timestamp obliczenia
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = "Wynik obliczenia"
        verbose_name_plural = "Wyniki obliczeń"

    def __str__(self):
        return f"{self.name}: {self.calculated_value} (z {self.source_id_1} i {self.source_id_2})"

    @classmethod
    def calculate_from_server_data(cls, name, id1, id2, operation_func):
        """
        Metoda klasowa do obliczania i zapisywania wyników na podstawie danych z ServerData.

        Parametry:
        - name: nazwa obliczenia do zapisania w rekordzie
        - id1, id2: identyfikatory ServerData do użycia w obliczeniu
        - operation_func: funkcja, która przyjmuje dwie wartości i zwraca obliczony wynik
        """
        try:
            # Pobierz najnowsze rekordy dla obu ID
            record1 = ServerData.objects.filter(server_id=id1).latest('timestamp')
            record2 = ServerData.objects.filter(server_id=id2).latest('timestamp')

            # Wykonaj obliczenie
            result_value = operation_func(record1.value, record2.value)

            # Zapisz wynik
            result = cls.objects.create(
                name=name,
                source_id_1=id1,
                source_id_2=id2,
                source_value_1=record1.value,
                source_value_2=record2.value,
                calculated_value=result_value
            )

            return result

        except ServerData.DoesNotExist:
            # Nie ma jeszcze rekordów dla jednego lub obu ID
            return None
        except Exception as e:
            # Obsługa innych błędów
            print(f"Błąd podczas obliczania wyniku: {e}")
            return None