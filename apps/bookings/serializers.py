from rest_framework import serializers

from apps.bookings.models import Booking, CallbackRequest, ukrainian_phone_validator
from apps.bookings.services import (
    BookingError,
    EquipmentNotAvailableError,
    InvalidDateRangeError,
    assert_dates_valid,
    create_booking,
)
from apps.catalog.models import Equipment
from apps.locations.models import City


class BookingSerializer(serializers.ModelSerializer):
    """Read-only representation of a :class:`~apps.bookings.models.Booking`,
    used for both the create response and the "my bookings" lookup list.
    Deliberately excludes contact info (name/phone/email) from the
    response body."""

    equipment_name = serializers.CharField(source="equipment.name", read_only=True)

    class Meta:
        model = Booking
        fields = (
            "number",
            "equipment_name",
            "start_date",
            "end_date",
            "delivery_method",
            "payment_method",
            "status",
            "rental_days",
            "price_per_day",
            "delivery_fee",
            "discount_amount",
            "total_price",
            "created_at",
        )
        read_only_fields = fields


class BookingCreateSerializer(serializers.Serializer):
    """Validates and creates a new booking for ``POST /api/bookings/``.

    A plain ``Serializer`` (not a ``ModelSerializer``) because the actual
    creation, pricing and availability logic lives in
    ``apps.bookings.services.create_booking`` — this only handles input
    shape/format validation.
    """

    equipment = serializers.SlugRelatedField(
        slug_field="slug", queryset=Equipment.objects.filter(is_active=True)
    )
    city = serializers.SlugRelatedField(
        slug_field="slug", queryset=City.objects.filter(is_active=True)
    )
    customer_name = serializers.CharField(max_length=150)
    customer_phone = serializers.CharField(
        max_length=20, validators=[ukrainian_phone_validator]
    )
    customer_email = serializers.EmailField(max_length=254)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    delivery_method = serializers.ChoiceField(choices=Booking.DeliveryMethod.choices)
    delivery_address = serializers.CharField(
        max_length=255, required=False, allow_blank=True, default=""
    )
    payment_method = serializers.ChoiceField(choices=Booking.PaymentMethod.choices)
    comment = serializers.CharField(required=False, allow_blank=True, default="")

    def validate(self, attrs):
        """Require `delivery_address` when `delivery_method` is courier.

        Args:
            attrs: The already field-validated input data.

        Returns:
            `attrs`, unchanged.

        Raises:
            rest_framework.exceptions.ValidationError: If courier delivery
                was chosen without an address.
        """
        if attrs["delivery_method"] == Booking.DeliveryMethod.COURIER and not attrs.get(
            "delivery_address"
        ):
            raise serializers.ValidationError(
                {"delivery_address": "Обов'язково для кур'єрської доставки."}
            )
        return attrs

    def create(self, validated_data):
        """Delegate to ``services.create_booking``.

        Args:
            validated_data: The validated input data.

        Returns:
            The newly created :class:`~apps.bookings.models.Booking`.

        Raises:
            EquipmentNotAvailableError: Re-raised as-is (not wrapped in a
                ``ValidationError``) so the view can map it to `409`
                instead of `400`.
            rest_framework.exceptions.ValidationError: Wraps any other
                :class:`~apps.bookings.services.BookingError`.
        """
        try:
            return create_booking(**validated_data)
        except EquipmentNotAvailableError:
            # A date conflict is a 409, not a validation error — the view
            # maps it, matching the callback-request endpoint.
            raise
        except BookingError as exc:
            raise serializers.ValidationError({"detail": str(exc)}) from exc

    def to_representation(self, instance):
        """Render the created booking through :class:`BookingSerializer`.

        Args:
            instance: The :class:`~apps.bookings.models.Booking` created
                by :meth:`create`.

        Returns:
            The serialized booking data (as a plain dict/OrderedDict).
        """
        return BookingSerializer(instance).data


class BookingQuoteSerializer(serializers.Serializer):
    """Validates input for ``POST /api/bookings/quote/`` — a price preview
    with no booking created and no availability check (only date format
    and range are validated)."""

    equipment = serializers.SlugRelatedField(
        slug_field="slug", queryset=Equipment.objects.filter(is_active=True)
    )
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    delivery_method = serializers.ChoiceField(choices=Booking.DeliveryMethod.choices)

    def validate(self, attrs):
        """Apply the same date rules a real booking would.

        Args:
            attrs: The already field-validated input data.

        Returns:
            `attrs`, unchanged.

        Raises:
            rest_framework.exceptions.ValidationError: If the date range
                is invalid (end before start, or start in the past) —
                otherwise `rental_days`/`total_price` could come out
                negative.
        """
        try:
            assert_dates_valid(attrs["start_date"], attrs["end_date"])
        except InvalidDateRangeError as exc:
            raise serializers.ValidationError({"end_date": str(exc)}) from exc
        return attrs


class BookingQuoteResponseSerializer(serializers.Serializer):
    """Renders quote_price()'s dict through proper DecimalFields.

    Without this, Response(plain_dict) would let DRF's JSON encoder fall
    back to float for Decimal values (e.g. 100.0 instead of "100.00").
    """

    rental_days = serializers.IntegerField()
    price_per_day = serializers.DecimalField(max_digits=8, decimal_places=2)
    delivery_fee = serializers.DecimalField(max_digits=8, decimal_places=2)
    total_price = serializers.DecimalField(max_digits=8, decimal_places=2)


class CallbackRequestSerializer(serializers.ModelSerializer):
    """Validates and represents a
    :class:`~apps.bookings.models.CallbackRequest` ("1-click booking")."""

    equipment = serializers.SlugRelatedField(
        slug_field="slug",
        queryset=Equipment.objects.filter(is_active=True),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = CallbackRequest
        fields = ("equipment", "phone", "start_date", "end_date", "comment")


class BookingCancelSerializer(serializers.Serializer):
    """Validates the request body for ``POST /api/bookings/{number}/cancel/``
    — just the phone number that must match the booking's `customer_phone`."""

    phone = serializers.CharField(max_length=20)
