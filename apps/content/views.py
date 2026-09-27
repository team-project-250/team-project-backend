from django.utils import timezone
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


class HeroSectionView(RetrieveAPIView):
    serializer_class = HeroSectionSerializer
    permission_classes = [AllowAny]

    def get_object(self):
        return HeroSection.load()


class AboutSectionView(RetrieveAPIView):
    serializer_class = AboutSectionSerializer
    permission_classes = [AllowAny]

    def get_object(self):
        return AboutSection.load()


class SiteSettingsView(RetrieveAPIView):
    serializer_class = SiteSettingsSerializer
    permission_classes = [AllowAny]

    def get_object(self):
        return SiteSettings.load()


class RentalStepListView(ListAPIView):
    queryset = RentalStep.objects.filter(is_active=True)
    serializer_class = RentalStepSerializer
    permission_classes = [AllowAny]
    pagination_class = None


class RentalTermListView(ListAPIView):
    queryset = RentalTerm.objects.filter(is_active=True)
    serializer_class = RentalTermSerializer
    permission_classes = [AllowAny]
    pagination_class = None


class DeliveryPaymentInfoView(RetrieveAPIView):
    serializer_class = DeliveryPaymentInfoSerializer
    permission_classes = [AllowAny]

    def get_object(self):
        return DeliveryPaymentInfo.load()


class HomePageView(APIView):
    """Aggregates every section the landing page needs into one response.

    Each piece is also available as its own resource (/api/content/hero/,
    /api/equipment/?is_popular=true, /api/reviews/, ...) for independent
    editing/testing — this endpoint just saves the frontend a round-trip
    per section on first paint.
    """

    permission_classes = [AllowAny]

    def get(self, request):
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
