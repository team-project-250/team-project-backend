from decimal import Decimal

from django.contrib import admin

from apps.bookings.models import Booking, CallbackRequest


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    """Django admin configuration for :class:`~apps.bookings.models.Booking`,
    with the manual 10% Instagram-discount bulk action."""

    list_display = (
        "number",
        "equipment",
        "customer_phone",
        "start_date",
        "end_date",
        "status",
        "total_price",
    )
    list_filter = ("status", "city", "delivery_method", "payment_method")
    search_fields = ("number", "customer_phone", "customer_name", "customer_email")
    readonly_fields = (
        "number",
        "rental_days",
        "price_per_day",
        "delivery_fee",
        "total_price",
        "created_at",
        "updated_at",
    )
    actions = ["apply_instagram_discount"]

    # "%%" is required: Django %-formats every action description against
    # model_format_dict(), so a literal "%" crashes the whole changelist.
    @admin.action(description="Apply 10%% Instagram discount")
    def apply_instagram_discount(self, request, queryset):
        """Apply a manual 10% discount to the selected bookings.

        Recomputes `discount_amount` and `total_price` from
        `price_per_day` / `rental_days` / `delivery_fee` for each booking
        in `queryset`. There's no automatic discount logic — this is the
        only place a discount is ever applied, and only by staff.

        Args:
            request: The current admin ``HttpRequest`` (used to display
                the confirmation message).
            queryset: The bookings selected in the admin changelist.
        """
        updated = 0
        for booking in queryset:
            subtotal = (
                booking.price_per_day * booking.rental_days + booking.delivery_fee
            )
            booking.discount_amount = (subtotal * Decimal("0.10")).quantize(
                Decimal("0.01")
            )
            booking.total_price = subtotal - booking.discount_amount
            booking.save(update_fields=["discount_amount", "total_price"])
            updated += 1
        self.message_user(request, f"Знижку застосовано до {updated} бронювань.")


@admin.register(CallbackRequest)
class CallbackRequestAdmin(admin.ModelAdmin):
    """Django admin configuration for
    :class:`~apps.bookings.models.CallbackRequest`, with a bulk action to
    mark leads processed once a manager has followed up."""

    list_display = (
        "phone",
        "equipment",
        "start_date",
        "end_date",
        "is_processed",
        "created_at",
    )
    list_filter = ("is_processed",)
    search_fields = ("phone",)
    actions = ["mark_processed"]

    @admin.action(description="Mark as processed")
    def mark_processed(self, request, queryset):
        """Mark the selected callback requests ``is_processed=True`` in bulk.

        Args:
            request: The current admin ``HttpRequest`` (used to display
                the confirmation message).
            queryset: The callback requests selected in the admin changelist.
        """
        updated = queryset.update(is_processed=True)
        self.message_user(request, f"{updated} заявок позначено обробленими.")
