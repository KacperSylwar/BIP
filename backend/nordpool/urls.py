from django.urls import path
from .views import LatestCalculatedResultView, ServerDataByIdView,BatteryChargeView,BatteryCharge10PercentView,BatteryCharge100PercentView,SolarAndGridPowerView, OptimizationDecisionView

urlpatterns = [
    # Istniejące URL-e
    path('latest-result/', LatestCalculatedResultView.as_view(), name='latest-result'),
    path('server-data/', ServerDataByIdView.as_view(), name='server-data'),

    # Nowe URL-e dla zarządzania baterią
    path('battery/charge/', BatteryChargeView.as_view(), name='battery-charge'),
    path('battery/charge-10/', BatteryCharge10PercentView.as_view(), name='battery-charge-10'),
    path('battery/charge-100/', BatteryCharge100PercentView.as_view(), name='battery-charge-100'),
path('solar-grid-power/', SolarAndGridPowerView.as_view(), name='solar-grid-power'),
path('optimization-decisions/', OptimizationDecisionView.as_view(), name='optimization-decisions'),
]