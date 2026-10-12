from rest_framework import serializers

from apps.content.models import (
    AboutFeature,
    AboutSection,
    DeliveryPaymentInfo,
    HeroSection,
    RentalStep,
    RentalTerm,
    SiteSettings,
)


class HeroSectionSerializer(serializers.ModelSerializer):
    """Serializes the singleton :class:`~apps.content.models.HeroSection`."""

    class Meta:
        model = HeroSection
        fields = ("title", "subtitle", "cta_label", "cta_url", "background_image")


class AboutFeatureSerializer(serializers.ModelSerializer):
    """Serializes one bullet in the "About EasyRent" feature list."""

    class Meta:
        model = AboutFeature
        fields = ("icon", "text")


class AboutSectionSerializer(serializers.ModelSerializer):
    """Serializes the singleton :class:`~apps.content.models.AboutSection`
    with its ordered feature list nested."""

    features = AboutFeatureSerializer(many=True, read_only=True)

    class Meta:
        model = AboutSection
        fields = ("title", "description", "features")


class RentalStepSerializer(serializers.ModelSerializer):
    """Serializes one "How to rent" step."""

    class Meta:
        model = RentalStep
        fields = ("order", "icon", "title", "description")


class RentalTermSerializer(serializers.ModelSerializer):
    """Serializes one "Rental terms" card."""

    class Meta:
        model = RentalTerm
        fields = ("order", "icon", "title", "description")


class DeliveryPaymentInfoSerializer(serializers.ModelSerializer):
    """Serializes the singleton
    :class:`~apps.content.models.DeliveryPaymentInfo`."""

    class Meta:
        model = DeliveryPaymentInfo
        fields = ("title", "description")


class SiteSettingsSerializer(serializers.ModelSerializer):
    """Serializes the singleton :class:`~apps.content.models.SiteSettings`
    (company/bank details for the IBAN-transfer payment method)."""

    class Meta:
        model = SiteSettings
        fields = (
            "company_name",
            "bank_name",
            "iban",
            "recipient_name",
            "edrpou",
            "transfer_note",
        )
