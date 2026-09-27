from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import viewsets

from apps.reviews.models import Review
from apps.reviews.serializers import ReviewSerializer


@extend_schema_view(
    list=extend_schema(
        summary="List published customer reviews",
        description=(
            "Returns moderated (`is_published=True`) reviews, newest first "
            "by `published_on`, paginated at 12 per page."
        ),
        tags=["reviews"],
    ),
    retrieve=extend_schema(
        summary="Get a single review",
        description="Returns one published review by id.",
        tags=["reviews"],
    ),
)
class ReviewViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only ``GET /api/reviews/`` and ``GET /api/reviews/{id}/``.

    Public, unauthenticated. Only ``is_published=True`` reviews are ever
    returned — moderation happens exclusively in the Django admin.
    """

    queryset = Review.objects.filter(is_published=True)
    serializer_class = ReviewSerializer
