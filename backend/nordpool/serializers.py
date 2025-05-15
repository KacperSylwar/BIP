from rest_framework import serializers
from .models import CalculatedResult, ServerData

class CalculatedResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = CalculatedResult
        fields = '__all__'

class ServerDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServerData
        fields = '__all__'