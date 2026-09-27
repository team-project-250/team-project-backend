from rest_framework.pagination import PageNumberPagination


class EquipmentPagination(PageNumberPagination):
    """8-per-page pagination for ``GET /api/equipment/`` (the global
    default is 12; the catalog grid is laid out for 8)."""

    page_size = 8
