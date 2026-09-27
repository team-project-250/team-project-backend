from django.contrib import admin

from apps.content.models import (
    AboutFeature,
    AboutSection,
    DeliveryPaymentInfo,
    HeroSection,
    RentalStep,
    RentalTerm,
    SiteSettings,
)


class SingletonAdmin(admin.ModelAdmin):
    """Base for models that must only ever have one row."""

    def has_add_permission(self, request):
        """Allow adding only when no row exists yet.

        Args:
            request: The current admin ``HttpRequest``.

        Returns:
            ``True`` if the model has zero rows, else ``False`` (hides the
            "Add" button once the singleton row has been created).
        """
        return not self.model.objects.exists()

    def has_delete_permission(self, request, obj=None):
        """Never allow deleting the singleton row.

        Args:
            request: The current admin ``HttpRequest``.
            obj: The instance being considered for deletion, if any.

        Returns:
            ``False``, always.
        """
        return False


@admin.register(HeroSection)
class HeroSectionAdmin(SingletonAdmin):
    """Django admin configuration for the
    :class:`~apps.content.models.HeroSection` singleton."""

    list_display = ("title", "cta_label", "updated_at")


class AboutFeatureInline(admin.TabularInline):
    """Inline editor for an about section's feature bullets."""

    model = AboutFeature
    extra = 1


@admin.register(AboutSection)
class AboutSectionAdmin(SingletonAdmin):
    """Django admin configuration for the
    :class:`~apps.content.models.AboutSection` singleton, with its feature
    list editable inline."""

    list_display = ("title", "updated_at")
    inlines = [AboutFeatureInline]


class OrderedContentAdmin(admin.ModelAdmin):
    """Base admin for simple ordered/active content lists (rental steps
    and terms), with `order`/`is_active` editable straight from the
    changelist."""

    list_display = ("title", "order", "is_active")
    list_editable = ("order", "is_active")
    list_display_links = ("title",)


@admin.register(RentalStep)
class RentalStepAdmin(OrderedContentAdmin):
    """Django admin configuration for
    :class:`~apps.content.models.RentalStep`."""


@admin.register(RentalTerm)
class RentalTermAdmin(OrderedContentAdmin):
    """Django admin configuration for
    :class:`~apps.content.models.RentalTerm`."""


@admin.register(SiteSettings)
class SiteSettingsAdmin(SingletonAdmin):
    """Django admin configuration for the
    :class:`~apps.content.models.SiteSettings` singleton."""

    list_display = ("company_name", "iban", "updated_at")


@admin.register(DeliveryPaymentInfo)
class DeliveryPaymentInfoAdmin(SingletonAdmin):
    """Django admin configuration for the
    :class:`~apps.content.models.DeliveryPaymentInfo` singleton."""

    list_display = ("title", "updated_at")
