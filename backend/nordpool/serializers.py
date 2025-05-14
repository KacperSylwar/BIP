from rest_framework import serializers
from .models import CalculatedResult

class CalculatedResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = CalculatedResult
        fields = '__all__'