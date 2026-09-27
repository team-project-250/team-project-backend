from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.catalog.models import (
    Category,
    Equipment,
    EquipmentBadge,
    EquipmentBenefit,
    EquipmentImage,
    EquipmentIncludedItem,
    EquipmentSpec,
    EquipmentUseCase,
)


class CategorySerializer(serializers.ModelSerializer):
    """Serializes a :class:`~apps.catalog.models.Category` for the
    categories list and as a nested field on equipment serializers."""

    class Meta:
        model = Category
        fields = ("id", "name", "slug")


class AvailabilitySerializer(serializers.Serializer):
    """Serializes the computed availability dict produced by
    ``apps.catalog.services.equipment_availability``/``annotate_availability``
    (never a model — availability is derived from bookings, not stored)."""

    status = serializers.ChoiceField(choices=["available", "booked"])
    available_from = serializers.DateField(allow_null=True)


class EquipmentListSerializer(serializers.ModelSerializer):
    """Serializes an :class:`~apps.catalog.models.Equipment` for catalog
    list views (a lighter shape than the detail page — no badges/specs/
    gallery, just what a catalog card needs)."""

    category = CategorySerializer(read_only=True)
    availability = AvailabilitySerializer(read_only=True)

    class Meta:
        model = Equipment
        fields = (
            "id",
            "name",
            "slug",
            "category",
            "price_per_day",
            "rating",
            "main_image",
            "is_popular",
            "availability",
        )


class EquipmentImageSerializer(serializers.ModelSerializer):
    """Serializes one gallery photo of an :class:`~apps.catalog.models.Equipment`."""

    class Meta:
        model = EquipmentImage
        fields = ("id", "image", "order")


class EquipmentSpecSerializer(serializers.ModelSerializer):
    """Serializes one label/value technical-specification row."""

    class Meta:
        model = EquipmentSpec
        fields = ("label", "value")


class EquipmentIncludedItemSerializer(serializers.ModelSerializer):
    """Serializes one "what's included" line item."""

    class Meta:
        model = EquipmentIncludedItem
        fields = ("name",)


class EquipmentBenefitSerializer(serializers.ModelSerializer):
    """Serializes one short benefit bullet shown next to the price."""

    class Meta:
        model = EquipmentBenefit
        fields = ("text",)


class EquipmentBadgeSerializer(serializers.ModelSerializer):
    """Serializes one free-form product badge (e.g. "Оригінал Karcher")."""

    class Meta:
        model = EquipmentBadge
        fields = ("label",)


class EquipmentUseCaseSerializer(serializers.ModelSerializer):
    """Serializes one "Техніка підходить для" line item."""

    class Meta:
        model = EquipmentUseCase
        fields = ("text",)


class EquipmentDetailSerializer(serializers.ModelSerializer):
    """Serializes the full product-page payload for one
    :class:`~apps.catalog.models.Equipment`: gallery, specs, included
    items, benefits, badges, use cases, available cities and breadcrumbs,
    on top of everything :class:`EquipmentListSerializer` already has."""

    category = CategorySerializer(read_only=True)
    availability = AvailabilitySerializer(read_only=True)
    images = EquipmentImageSerializer(many=True, read_only=True)
    specs = EquipmentSpecSerializer(many=True, read_only=True)
    included_items = EquipmentIncludedItemSerializer(many=True, read_only=True)
    benefits = EquipmentBenefitSerializer(many=True, read_only=True)
    badges = EquipmentBadgeSerializer(many=True, read_only=True)
    suitable_for = EquipmentUseCaseSerializer(many=True, read_only=True)
    available_cities = serializers.SlugRelatedField(
        slug_field="slug", many=True, read_only=True
    )
    breadcrumbs = serializers.SerializerMethodField()

    class Meta:
        model = Equipment
        fields = (
            "id",
            "name",
            "slug",
            "sku",
            "category",
            "short_description",
            "description",
            "price_per_day",
            "rating",
            "main_image",
            "availability",
            "badges",
            "images",
            "specs",
            "included_items",
            "benefits",
            "suitable_for",
            "available_cities",
            "breadcrumbs",
        )

    @extend_schema_field(
        {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "label": {"type": "string"},
                    "url": {"type": "string", "nullable": True},
                },
            },
        }
    )
    def get_breadcrumbs(self, obj: Equipment) -> list[dict]:
        """Build the breadcrumb trail for this equipment's product page.

        Args:
            obj: The :class:`~apps.catalog.models.Equipment` being serialized.

        Returns:
            A list of ``{"label": str, "url": str | None}`` steps, from the
            home page down to the equipment itself (whose ``url`` is
            ``None``, since it's the current page).
        """
        return [
            {"label": "Головна", "url": "/"},
            {"label": "Каталог", "url": "/catalog"},
            {
                "label": obj.category.name,
                "url": f"/catalog?category={obj.category.slug}",
            },
            {"label": obj.name, "url": None},
        ]
