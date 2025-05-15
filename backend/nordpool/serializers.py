from rest_framework import serializers
from .models import CalculatedResult, ServerData, SimulatedBattery, SimulatedSolarAndGridPower, OptimizationDecision

class CalculatedResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = CalculatedResult
        fields = '__all__'

class ServerDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServerData
        fields = '__all__'

class SimulatedBatterySerializer(serializers.ModelSerializer):
    class Meta:
        model = SimulatedBattery
        fields = '__all__'
        read_only_fields = ['last_updated']

class SimulatedSolarAndGridPowerSerializer(serializers.ModelSerializer):
    class Meta:
        model = SimulatedSolarAndGridPower
        fields = '__all__'
        read_only_fields = ['last_updated']

class OptimizationDecisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = OptimizationDecision
        fields = '__all__'