from django.urls import path
from .views import LatestCalculatedResultView, ServerDataByIdView

urlpatterns = [
    path('latest-result/', LatestCalculatedResultView.as_view(), name='latest-result'),
    path('server-data/', ServerDataByIdView.as_view(), name='server-data'),  # Usunięto parametr URL
]