from rest_framework import serializers

from apps.locations.models import City


class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = (
            "id",
            "name",
            "slug",
            "is_default",
            "pickup_address",
            "pickup_phone",
            "working_hours",
        )
