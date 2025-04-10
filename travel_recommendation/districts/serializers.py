from rest_framework import serializers
from .models import District

class DistrictSerializer(serializers.ModelSerializer):
    class Meta:
        model = District
        fields = ['name', 'latitude', 'longitude']

class TopDistrictSerializer(serializers.Serializer):
    name = serializers.CharField()
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()
    avg_temperature = serializers.FloatField()
    avg_pm25 = serializers.FloatField()

class TravelRecommendationSerializer(serializers.Serializer):
    recommendation = serializers.CharField()
    reason = serializers.CharField()