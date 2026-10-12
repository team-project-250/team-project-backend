from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import viewsets

from apps.locations.models import City
from apps.locations.serializers import CitySerializer


@extend_schema_view(
    list=extend_schema(
        summary="List active service cities",
        description=(
            "Returns every active city with its pickup point, ordered for "
            "the header/footer city selector. Not paginated — the city "
            "list is always small."
        ),
        tags=["locations"],
    ),
    retrieve=extend_schema(
        summary="Get a single city",
        description="Returns one active city by its slug.",
        tags=["locations"],
    ),
)
class CityViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only ``GET /api/cities/`` and ``GET /api/cities/{slug}/``.

    Public, unauthenticated (see the project's "no customer auth" design).
    Only cities with ``is_active=True`` are ever returned.
    """

    queryset = City.objects.filter(is_active=True)
    serializer_class = CitySerializer
    lookup_field = "slug"
    pagination_class = None
