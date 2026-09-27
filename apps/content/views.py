from django.utils import timezone
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.models import Category, Equipment
from apps.catalog.serializers import CategorySerializer, EquipmentListSerializer
from apps.catalog.services import annotate_availability
from apps.content.models import (
    AboutSection,
    DeliveryPaymentInfo,
    HeroSection,
    RentalStep,
    RentalTerm,
    SiteSettings,
)
from apps.content.serializers import (
    AboutSectionSerializer,
    DeliveryPaymentInfoSerializer,
    HeroSectionSerializer,
    RentalStepSerializer,
    RentalTermSerializer,
    SiteSettingsSerializer,
)
from apps.locations.models import City
from apps.locations.serializers import CitySerializer
from apps.reviews.models import Review
from apps.reviews.serializers import ReviewSerializer


@extend_schema(
    summary="Get the home page hero section",
    description="Title, subtitle, CTA and background image — editable in "
    "the admin. Self-heals (returns a blank row) if the database is empty.",
    tags=["content"],
)
class HeroSectionView(RetrieveAPIView):
    """``GET /api/content/hero/``. Public, unauthenticated."""

    serializer_class = HeroSectionSerializer
    permission_classes = [AllowAny]

    def get_object(self):
        """Return the singleton hero section, creating it if needed.

        Returns:
            The single :class:`~apps.content.models.HeroSection` row.
        """
        return HeroSection.load()


@extend_schema(
    summary="Get the home page about section",
    description="Title, description and its ordered feature list.",
    tags=["content"],
)
class AboutSectionView(RetrieveAPIView):
    """``GET /api/content/about/``. Public, unauthenticated."""

    serializer_class = AboutSectionSerializer
    permission_classes = [AllowAny]

    def get_object(self):
        """Return the singleton about section, creating it if needed.

        Returns:
            The single :class:`~apps.content.models.AboutSection` row.
        """
        return AboutSection.load()


@extend_schema(
    summary="Get company/bank settings",
    description="Shown after a customer picks the IBAN-transfer payment method.",
    tags=["content"],
)
class SiteSettingsView(RetrieveAPIView):
    """``GET /api/content/settings/``. Public, unauthenticated."""

    serializer_class = SiteSettingsSerializer
    permission_classes = [AllowAny]

    def get_object(self):
        """Return the singleton site settings, creating it if needed.

        Returns:
            The single :class:`~apps.content.models.SiteSettings` row.
        """
        return SiteSettings.load()


@extend_schema(
    summary='List "How to rent" steps',
    description="Active steps only, ordered. Not paginated.",
    tags=["content"],
)
class RentalStepListView(ListAPIView):
    """``GET /api/content/rental-steps/``. Public, unauthenticated."""

    queryset = RentalStep.objects.filter(is_active=True)
    serializer_class = RentalStepSerializer
    permission_classes = [AllowAny]
    pagination_class = None


@extend_schema(
    summary="List rental terms",
    description="Active terms only, ordered. Not paginated.",
    tags=["content"],
)
class RentalTermListView(ListAPIView):
    """``GET /api/content/rental-terms/``. Public, unauthenticated."""

    queryset = RentalTerm.objects.filter(is_active=True)
    serializer_class = RentalTermSerializer
    permission_classes = [AllowAny]
    pagination_class = None


@extend_schema(
    summary="Get the delivery & payment info",
    description='"Доставка і оплата" product-page tab content — global, '
    "the same for every product.",
    tags=["content"],
)
class DeliveryPaymentInfoView(RetrieveAPIView):
    """``GET /api/content/delivery-payment/``. Public, unauthenticated."""

    serializer_class = DeliveryPaymentInfoSerializer
    permission_classes = [AllowAny]

    def get_object(self):
        """Return the singleton delivery/payment info, creating it if needed.

        Returns:
            The single :class:`~apps.content.models.DeliveryPaymentInfo` row.
        """
        return DeliveryPaymentInfo.load()


class HomePageView(APIView):
    """Aggregates every section the landing page needs into one response.

    Each piece is also available as its own resource (/api/content/hero/,
    /api/equipment/?is_popular=true, /api/reviews/, ...) for independent
    editing/testing — this endpoint just saves the frontend a round-trip
    per section on first paint.
    """

    permission_classes = [AllowAny]

    @extend_schema(
        summary="Get the landing page in one request",
        description=(
            "Aggregates hero, about, rental steps/terms, settings, cities, "
            "categories, up to 8 popular equipment items and up to 6 "
            "published reviews."
        ),
        responses={
            200: inline_serializer(
                name="HomePageResponse",
                fields={
                    "hero": HeroSectionSerializer(),
                    "about": AboutSectionSerializer(),
                    "rental_steps": RentalStepSerializer(many=True),
                    "rental_terms": RentalTermSerializer(many=True),
                    "settings": SiteSettingsSerializer(),
                    "cities": CitySerializer(many=True),
                    "categories": CategorySerializer(many=True),
                    "popular_equipment": EquipmentListSerializer(many=True),
                    "reviews": ReviewSerializer(many=True),
                },
            ),
        },
        tags=["content"],
    )
    def get(self, request):
        """Serve ``GET /api/home/``.

        Args:
            request: The current request (unused — this endpoint takes no
                parameters).

        Returns:
            `200` with the aggregated landing-page payload described above.
        """
        popular_equipment = list(
            Equipment.objects.filter(is_active=True, is_popular=True)
            .select_related("category")
            .order_by("-rating")[:8]
        )
        annotate_availability(popular_equipment, timezone.localdate())

        data = {
            "hero": HeroSectionSerializer(HeroSection.load()).data,
            "about": AboutSectionSerializer(AboutSection.load()).data,
            "rental_steps": RentalStepSerializer(
                RentalStep.objects.filter(is_active=True), many=True
            ).data,
            "rental_terms": RentalTermSerializer(
                RentalTerm.objects.filter(is_active=True), many=True
            ).data,
            "settings": SiteSettingsSerializer(SiteSettings.load()).data,
            "cities": CitySerializer(
                City.objects.filter(is_active=True), many=True
            ).data,
            "categories": CategorySerializer(
                Category.objects.filter(is_active=True), many=True
            ).data,
            "popular_equipment": EquipmentListSerializer(
                popular_equipment, many=True
            ).data,
            "reviews": ReviewSerializer(
                Review.objects.filter(is_published=True)[:6], many=True
            ).data,
        }
        return Response(data)
