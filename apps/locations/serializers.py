from rest_framework import serializers

from apps.locations.models import City


class CitySerializer(serializers.ModelSerializer):
    """Serializes a :class:`~apps.locations.models.City` for the public
    city list/detail endpoints, including its pickup-point details."""

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
