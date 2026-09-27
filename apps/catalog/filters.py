import django_filters
from django.utils import timezone

from apps.bookings.models import Booking
from apps.catalog.models import Equipment


class EquipmentFilter(django_filters.FilterSet):
    category = django_filters.CharFilter(method="filter_category")
    city = django_filters.CharFilter(method="filter_city")
    price_min = django_filters.NumberFilter(
        field_name="price_per_day", lookup_expr="gte"
    )
    price_max = django_filters.NumberFilter(
        field_name="price_per_day", lookup_expr="lte"
    )
    is_popular = django_filters.BooleanFilter()
    availability = django_filters.CharFilter(method="filter_availability")

    class Meta:
        model = Equipment
        fields: list[str] = []

    def filter_category(self, queryset, name, value):
        slugs = [s.strip() for s in value.split(",") if s.strip()]
        return queryset.filter(category__slug__in=slugs)

    def filter_city(self, queryset, name, value):
        slugs = [s.strip() for s in value.split(",") if s.strip()]
        return queryset.filter(available_cities__slug__in=slugs).distinct()

    def filter_availability(self, queryset, name, value):
        today = timezone.localdate()
        booked_ids = Booking.objects.filter(
            status__in=Booking.ACTIVE_STATUSES,
            start_date__lte=today,
            end_date__gte=today,
        ).values_list("equipment_id", flat=True)
        if value == "booked":
            return queryset.filter(id__in=booked_ids)
        if value == "available":
            return queryset.exclude(id__in=booked_ids)
        return queryset
