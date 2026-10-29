from rest_framework.pagination import PageNumberPagination


class EquipmentPagination(PageNumberPagination):
    """6-per-page pagination for ``GET /api/equipment/`` (the global
    default is 12; the catalog grid is laid out for 6).

    ``?page_size=`` lets other views ask for a bigger page in one request
    (e.g. the mega menu listing a whole category), capped at
    ``max_page_size`` so a client can't pull the entire table at once.
    """

    page_size = 6
    page_size_query_param = "page_size"
    max_page_size = 50
