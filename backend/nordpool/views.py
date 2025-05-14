from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import CalculatedResult
from .serializers import CalculatedResultSerializer


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