import calendar
from datetime import date, timedelta

from django.utils import timezone
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


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer
    pagination_class = None


class EquipmentViewSet(viewsets.ReadOnlyModelViewSet):
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
        if self.action == "list":
            return EquipmentListSerializer
        return EquipmentDetailSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        exclude_slug = self.request.query_params.get("exclude")
        if exclude_slug:
            queryset = queryset.exclude(slug=exclude_slug)
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        target = list(page if page is not None else queryset)
        annotate_availability(target, timezone.localdate())
        serializer = self.get_serializer(target, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.availability = equipment_availability(instance, timezone.localdate())
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def availability(self, request, slug=None):
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

    @action(detail=True, methods=["get"])
    def related(self, request, slug=None):
        """ "Інша техніка" carousel — same category first, then filled with
        other active equipment. `?limit=` defaults to 3, capped at 12."""
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
