import calendar
from datetime import date, timedelta

from django.utils import timezone
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    extend_schema,
    extend_schema_view,
)
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.bookings.models import Booking
from apps.catalog.filters import EquipmentFilter
from apps.catalog.models import Category, Equipment
from apps.catalog.pagination import EquipmentPagination
from apps.catalog.serializers import (
    CategorySerializer,
    EquipmentDetailSerializer,
    EquipmentListSerializer,
)
from apps.catalog.services import (
    annotate_availability,
    equipment_availability,
    related_equipment,
)


@extend_schema_view(
    list=extend_schema(
        summary="List active equipment categories",
        description="Returns every active category, ordered for catalog navigation.",
        tags=["catalog"],
    ),
    retrieve=extend_schema(summary="Get a single category", tags=["catalog"]),
)
class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only ``GET /api/categories/``. Public, unauthenticated; only
    ``is_active=True`` categories are ever returned."""

    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer
    pagination_class = None


@extend_schema_view(
    list=extend_schema(
        summary="List equipment (catalog grid)",
        description=(
            "Filterable, searchable, paginated (8/page) list of active "
            "equipment. Each item includes a computed `availability` "
            "(never stored — derived from bookings for today)."
        ),
        parameters=[
            OpenApiParameter(
                "category", str, description="Comma-separated category slugs."
            ),
            OpenApiParameter("city", str, description="Comma-separated city slugs."),
            OpenApiParameter("price_min", float, description="Minimum price/day."),
            OpenApiParameter("price_max", float, description="Maximum price/day."),
            OpenApiParameter("is_popular", bool),
            OpenApiParameter(
                "availability",
                str,
                enum=["available", "booked"],
                description="Filter by today's computed availability.",
            ),
            OpenApiParameter("search", str, description="Free-text search."),
            OpenApiParameter(
                "ordering",
                str,
                description="`rating` (default, descending) or `price_per_day`.",
            ),
            OpenApiParameter(
                "exclude", str, description="A slug to exclude from the results."
            ),
        ],
        tags=["catalog"],
    ),
    retrieve=extend_schema(
        summary="Get one equipment's full product-page detail",
        description="Specs, gallery, included items, benefits, badges, "
        "`suitable_for`, breadcrumbs, available cities and `availability`.",
        tags=["catalog"],
    ),
)
class EquipmentViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only equipment endpoints: catalog list/detail plus the
    ``availability`` and ``related`` sub-actions below.

    Public, unauthenticated. Only ``is_active=True`` equipment is ever
    returned.
    """

    queryset = (
        Equipment.objects.filter(is_active=True)
        .select_related("category")
        .prefetch_related(
            "images", "specs", "included_items", "benefits", "available_cities"
        )
    )
    lookup_field = "slug"
    pagination_class = EquipmentPagination
    filterset_class = EquipmentFilter
    search_fields = ("name", "sku", "short_description")
    ordering_fields = ("rating", "price_per_day")

    def get_serializer_class(self):
        """Use the lighter list serializer for ``list``, the full detail
        serializer for every other action (retrieve, related, ...).

        Returns:
            The serializer class to use for the current action.
        """
        if self.action == "list":
            return EquipmentListSerializer
        return EquipmentDetailSerializer

    def get_queryset(self):
        """Return the base queryset, optionally excluding one slug.

        Returns:
            The (possibly filtered) equipment queryset. Honors the
            `?exclude=<slug>` query parameter used by the "related
            equipment" carousel to drop the item already being viewed.
        """
        queryset = super().get_queryset()
        exclude_slug = self.request.query_params.get("exclude")
        if exclude_slug:
            queryset = queryset.exclude(slug=exclude_slug)
        return queryset

    def list(self, request, *args, **kwargs):
        """Serve ``GET /api/equipment/`` with availability annotated in
        one extra query (not per-item, to avoid N+1).

        Args:
            request: The current request.
            *args: Unused; required by DRF's view method signature.
            **kwargs: Unused; required by DRF's view method signature.

        Returns:
            A paginated (or plain, if pagination is disabled) ``Response``
            of serialized equipment.
        """
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        target = list(page if page is not None else queryset)
        annotate_availability(target, timezone.localdate())
        serializer = self.get_serializer(target, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        """Serve ``GET /api/equipment/{slug}/`` with today's availability
        computed and attached to the instance before serialization.

        Args:
            request: The current request.
            *args: Unused; required by DRF's view method signature.
            **kwargs: Unused; required by DRF's view method signature.

        Returns:
            A ``Response`` with the serialized equipment detail.
        """
        instance = self.get_object()
        instance.availability = equipment_availability(instance, timezone.localdate())
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @extend_schema(
        summary="Get booked dates for one month",
        description=(
            "Returns every date in the given month that overlaps an active "
            "booking for this equipment — used to render the calendar in "
            "the date picker."
        ),
        parameters=[
            OpenApiParameter(
                "month",
                str,
                description="`YYYY-MM`; defaults to the current month.",
            ),
        ],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "month": {"type": "string", "example": "2026-09"},
                    "unavailable_dates": {
                        "type": "array",
                        "items": {"type": "string", "format": "date"},
                    },
                },
            },
            400: {
                "type": "object",
                "properties": {"month": {"type": "array", "items": {"type": "string"}}},
            },
        },
        examples=[
            OpenApiExample(
                "Booked days",
                value={
                    "month": "2026-09",
                    "unavailable_dates": ["2026-09-29", "2026-09-30"],
                },
                response_only=True,
            ),
        ],
        tags=["catalog"],
    )
    @action(detail=True, methods=["get"])
    def availability(self, request, slug=None):
        """Serve ``GET /api/equipment/{slug}/availability/?month=YYYY-MM``.

        Args:
            request: The current request; may carry a `month` query param.
            slug: The equipment's slug (from the URL).

        Returns:
            `200` with `{"month", "unavailable_dates"}` on success, or
            `400` if `month` isn't a valid `YYYY-MM` string.
        """
        equipment = self.get_object()
        month_param = request.query_params.get("month")
        today = timezone.localdate()
        if month_param:
            try:
                year, month = (int(part) for part in month_param.split("-"))
                # calendar.monthrange / date() would raise (-> 500) otherwise.
                if not (1 <= month <= 12 and 1 <= year <= 9999):
                    raise ValueError(month_param)
            except ValueError:
                return Response(
                    {"month": ["Use YYYY-MM format."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            year, month = today.year, today.month

        days_in_month = calendar.monthrange(year, month)[1]
        range_start = date(year, month, 1)
        range_end = date(year, month, days_in_month)

        bookings = Booking.objects.filter(
            equipment=equipment,
            status__in=Booking.ACTIVE_STATUSES,
            start_date__lte=range_end,
            end_date__gte=range_start,
        )
        unavailable = set()
        for booking in bookings:
            day = max(booking.start_date, range_start)
            last = min(booking.end_date, range_end)
            while day <= last:
                unavailable.add(day.isoformat())
                day += timedelta(days=1)

        return Response(
            {
                "month": f"{year:04d}-{month:02d}",
                "unavailable_dates": sorted(unavailable),
            }
        )

    @extend_schema(
        summary='"Інша техніка" — related equipment',
        description=(
            "Same category first, then filled with other active equipment. "
            "Never includes the equipment itself."
        ),
        parameters=[
            OpenApiParameter("limit", int, description="Defaults to 3, capped at 12."),
        ],
        responses={200: EquipmentListSerializer(many=True)},
        tags=["catalog"],
    )
    @action(detail=True, methods=["get"])
    def related(self, request, slug=None):
        """Serve ``GET /api/equipment/{slug}/related/?limit=``.

        Args:
            request: The current request; may carry a `limit` query param.
            slug: The equipment's slug (from the URL).

        Returns:
            `200` with a list of serialized related equipment, or `400` if
            `limit` isn't an integer.
        """
        equipment = self.get_object()
        try:
            limit = int(request.query_params.get("limit", 3))
        except ValueError:
            return Response(
                {"limit": ["Must be an integer."]}, status=status.HTTP_400_BAD_REQUEST
            )
        limit = max(1, min(limit, 12))

        items = related_equipment(equipment, limit=limit)
        annotate_availability(items, timezone.localdate())
        serializer = EquipmentListSerializer(items, many=True)
        return Response(serializer.data)
