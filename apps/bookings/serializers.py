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
        if attrs["delivery_method"] == Booking.DeliveryMethod.COURIER and not attrs.get(
            "delivery_address"
        ):
            raise serializers.ValidationError(
                {"delivery_address": "Обов'язково для кур'єрської доставки."}
            )
        return attrs

    def create(self, validated_data):
        try:
            return create_booking(**validated_data)
        except EquipmentNotAvailableError:
            # A date conflict is a 409, not a validation error — the view
            # maps it, matching the callback-request endpoint.
            raise
        except BookingError as exc:
            raise serializers.ValidationError({"detail": str(exc)}) from exc

    def to_representation(self, instance):
        return BookingSerializer(instance).data


class BookingQuoteSerializer(serializers.Serializer):
    equipment = serializers.SlugRelatedField(
        slug_field="slug", queryset=Equipment.objects.filter(is_active=True)
    )
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    delivery_method = serializers.ChoiceField(choices=Booking.DeliveryMethod.choices)

    def validate(self, attrs):
        # Same date rules as a real booking — otherwise end < start yields a
        # negative rental_days / total_price.
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
    phone = serializers.CharField(max_length=20)
