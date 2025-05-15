from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import CalculatedResult, ServerData
from .serializers import CalculatedResultSerializer, ServerDataSerializer


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