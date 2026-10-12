from rest_framework import serializers

from apps.reviews.models import Review


class ReviewSerializer(serializers.ModelSerializer):
    """Serializes a published :class:`~apps.reviews.models.Review` for the
    public reviews list and the home-page aggregator."""

    class Meta:
        model = Review
        fields = ("id", "author_name", "avatar", "rating", "text", "published_on")
