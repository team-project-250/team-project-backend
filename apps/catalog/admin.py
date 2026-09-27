from django.contrib import admin
from django.utils.html import format_html

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


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Django admin configuration for :class:`~apps.catalog.models.Category`."""

    list_display = ("name", "order", "is_active")
    list_editable = ("order", "is_active")
    prepopulated_fields = {"slug": ("name",)}


class EquipmentImageInline(admin.TabularInline):
    """Inline editor for an equipment's gallery photos."""

    model = EquipmentImage
    extra = 1


class EquipmentSpecInline(admin.TabularInline):
    """Inline editor for an equipment's technical specifications."""

    model = EquipmentSpec
    extra = 1


class EquipmentIncludedItemInline(admin.TabularInline):
    """Inline editor for an equipment's "what's included" list."""

    model = EquipmentIncludedItem
    extra = 1


class EquipmentBenefitInline(admin.TabularInline):
    """Inline editor for an equipment's short benefit bullets."""

    model = EquipmentBenefit
    extra = 1


class EquipmentBadgeInline(admin.TabularInline):
    """Inline editor for an equipment's free-form product badges."""

    model = EquipmentBadge
    extra = 1


class EquipmentUseCaseInline(admin.TabularInline):
    """Inline editor for an equipment's "Техніка підходить для" list."""

    model = EquipmentUseCase
    extra = 1


@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    """Django admin configuration for :class:`~apps.catalog.models.Equipment`,
    with inline editors for every related list (gallery, specs, included
    items, benefits, badges, use cases) and an image preview/thumbnail."""

    list_display = (
        "thumbnail",
        "name",
        "category",
        "price_per_day",
        "rating",
        "is_popular",
        "is_active",
    )
    list_display_links = ("thumbnail", "name")
    list_filter = ("category", "is_popular", "is_active", "available_cities")
    search_fields = ("name", "sku")
    prepopulated_fields = {"slug": ("name",)}
    filter_horizontal = ("available_cities",)
    readonly_fields = ("created_at", "preview")
    fieldsets = (
        (None, {"fields": ("name", "slug", "sku", "category")}),
        ("Опис", {"fields": ("short_description", "description")}),
        ("Ціна та рейтинг", {"fields": ("price_per_day", "rating")}),
        ("Показ на сайті", {"fields": ("is_popular", "is_active", "available_cities")}),
        ("Фото", {"fields": ("main_image", "preview")}),
        ("Службове", {"fields": ("created_at",)}),
    )
    inlines = [
        EquipmentImageInline,
        EquipmentSpecInline,
        EquipmentIncludedItemInline,
        EquipmentBenefitInline,
        EquipmentBadgeInline,
        EquipmentUseCaseInline,
    ]

    @admin.display(description="Фото")
    def thumbnail(self, obj):
        """Render a small thumbnail of ``obj.main_image`` for the changelist.

        Args:
            obj: The :class:`~apps.catalog.models.Equipment` row being rendered.

        Returns:
            Safe HTML for an ``<img>`` tag, or ``"—"`` if there's no image.
        """
        if obj.main_image:
            return format_html('<img src="{}" style="height:40px">', obj.main_image.url)
        return "—"

    @admin.display(description="Попередній перегляд")
    def preview(self, obj):
        """Render a larger preview of ``obj.main_image`` on the change form.

        Args:
            obj: The :class:`~apps.catalog.models.Equipment` being edited.

        Returns:
            Safe HTML for an ``<img>`` tag, or a placeholder string if
            there's no image yet.
        """
        if obj.main_image:
            return format_html(
                '<img src="{}" style="max-height:200px">', obj.main_image.url
            )
        return "Фото ще не завантажено"
