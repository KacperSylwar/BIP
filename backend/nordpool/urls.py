from django.urls import path
from .views import LatestCalculatedResultView

urlpatterns = [
    path('latest-result/', LatestCalculatedResultView.as_view(), name='latest-result'),
]