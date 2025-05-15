from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import CalculatedResult, ServerData, SimulatedBattery, SimulatedSolarAndGridPower,OptimizationDecision
from .serializers import CalculatedResultSerializer, ServerDataSerializer, SimulatedBatterySerializer, SimulatedSolarAndGridPowerSerializer, OptimizationDecisionSerializer


class LatestCalculatedResultView(APIView):
    """
    API endpoint zwracający tylko najnowszy wynik obliczeń.
    """

    def get(self, request):
        try:
            # Pobierz najnowszy rekord (dzięki Meta.ordering w modelu)
            latest_result = CalculatedResult.objects.first()

            if not latest_result:
                return Response({"detail": "Brak wyników"}, status=status.HTTP_404_NOT_FOUND)

            serializer = CalculatedResultSerializer(latest_result)
            return Response(serializer.data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ServerDataByIdView(APIView):
    """
    API endpoint zwracający najnowsze dane z ServerData dla predefiniowanego server_id.
    """
    # Zdefiniowany na stałe ID
    SERVER_ID = "9@-685@V"  # możesz też użyć "7@1042@V" lub innego ID

    def get(self, request):
        try:
            # Pobierz najnowszy rekord dla predefiniowanego server_id
            server_data = ServerData.objects.filter(server_id=self.SERVER_ID).first()

            if not server_data:
                return Response({"detail": f"Brak danych dla ID: {self.SERVER_ID}"},
                               status=status.HTTP_404_NOT_FOUND)

            serializer = ServerDataSerializer(server_data)
            return Response(serializer.data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


from decimal import Decimal
from .models import SimulatedBattery
from .serializers import SimulatedBatterySerializer


class BatteryChargeView(APIView):
    """
    API endpoint do zarządzania poziomem naładowania baterii.
    """

    def get(self, request):
        """Pobiera aktualny stan baterii"""
        try:
            battery = SimulatedBattery.objects.first()
            if not battery:
                return Response({"detail": "Brak baterii w systemie"}, status=status.HTTP_404_NOT_FOUND)
            serializer = SimulatedBatterySerializer(battery)
            return Response(serializer.data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        """Ustawia dowolny poziom naładowania baterii"""
        try:
            battery = SimulatedBattery.objects.first()
            if not battery:
                return Response({"detail": "Brak baterii w systemie"}, status=status.HTTP_404_NOT_FOUND)

            charge_level = request.data.get('charge_level')
            if charge_level is None:
                return Response({"error": "Wymagany parametr charge_level"}, status=status.HTTP_400_BAD_REQUEST)

            try:
                charge_level = Decimal(charge_level)
            except:
                return Response({"error": "charge_level musi być liczbą"}, status=status.HTTP_400_BAD_REQUEST)

            if charge_level < 0 or charge_level > battery.capacity:
                return Response({"error": f"charge_level musi być między 0 a {battery.capacity}"},
                                status=status.HTTP_400_BAD_REQUEST)

            battery.current_charge = charge_level
            battery.save()

            serializer = SimulatedBatterySerializer(battery)
            return Response(serializer.data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class BatteryCharge10PercentView(APIView):
    """
    API endpoint do ładowania baterii do 10% pojemności.
    """

    def post(self, request):
        try:
            battery = SimulatedBattery.objects.first()
            if not battery:
                return Response({"detail": "Brak baterii w systemie"}, status=status.HTTP_404_NOT_FOUND)

            battery.current_charge = Decimal('0.1') * battery.capacity
            battery.save()

            serializer = SimulatedBatterySerializer(battery)
            return Response(serializer.data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class BatteryCharge100PercentView(APIView):
    """
    API endpoint do ładowania baterii do 100% pojemności.
    """

    def post(self, request):
        try:
            battery = SimulatedBattery.objects.first()
            if not battery:
                return Response({"detail": "Brak baterii w systemie"}, status=status.HTTP_404_NOT_FOUND)

            battery.current_charge = battery.capacity
            battery.save()

            serializer = SimulatedBatterySerializer(battery)
            return Response(serializer.data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class SolarAndGridPowerView(APIView):
        """
        API endpoint do odczytu najnowszych danych o mocy z paneli solarnych i sieci.
        """

        def get(self, request):
            """Pobiera aktualny stan mocy"""
            try:
                power_data = SimulatedSolarAndGridPower.objects.first()
                if not power_data:
                    return Response({"detail": "Brak danych w systemie"}, status=status.HTTP_404_NOT_FOUND)
                serializer = SimulatedSolarAndGridPowerSerializer(power_data)
                return Response(serializer.data)
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class OptimizationDecisionView(APIView):
    """
    API endpoint do pobierania historii decyzji algorytmu optymalizacji energii.
    """

    def get(self, request):
        try:
            # Pobierz ostatnią lub określoną liczbę decyzji
            limit = request.query_params.get('limit', 10)
            try:
                limit = int(limit)
                if limit <= 0:
                    limit = 10
            except ValueError:
                limit = 10

            decisions = OptimizationDecision.objects.all()[:limit]

            if not decisions:
                return Response({"detail": "Brak historii decyzji"}, status=status.HTTP_404_NOT_FOUND)

            serializer = OptimizationDecisionSerializer(decisions, many=True)
            return Response(serializer.data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)