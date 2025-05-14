from django.db import models



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
    server_id = models.CharField(max_length=20, unique=True, verbose_name="ID")
    value = models.DecimalField(max_digits=20, decimal_places=12)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = "Dane z serwera"
        verbose_name_plural = "Dane z serwera"

    def __str__(self):
        return f"ID: {self.server_id} - Wartość: {self.value}"