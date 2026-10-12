from django.contrib import admin

from apps.locations.models import City


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ("name", "is_default", "is_active", "order", "pickup_phone")
    list_editable = ("is_default", "is_active", "order")
    list_display_links = ("name",)
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "pickup_address")
