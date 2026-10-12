from rest_framework import viewsets

from apps.locations.models import City
from apps.locations.serializers import CitySerializer


class CityViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = City.objects.filter(is_active=True)
    serializer_class = CitySerializer
    lookup_field = "slug"
    pagination_class = None
