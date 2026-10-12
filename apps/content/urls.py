"""Content API routes — editable homepage sections + the home aggregator."""

from django.urls import path

from apps.content.views import (
    AboutSectionView,
    DeliveryPaymentInfoView,
    HeroSectionView,
    HomePageView,
    RentalStepListView,
    RentalTermListView,
    SiteSettingsView,
)

app_name = "content"

urlpatterns = [
    path("content/hero/", HeroSectionView.as_view(), name="hero"),
    path("content/about/", AboutSectionView.as_view(), name="about"),
    path("content/rental-steps/", RentalStepListView.as_view(), name="rental-steps"),
    path("content/rental-terms/", RentalTermListView.as_view(), name="rental-terms"),
    path(
        "content/delivery-payment/",
        DeliveryPaymentInfoView.as_view(),
        name="delivery-payment",
    ),
    path("content/settings/", SiteSettingsView.as_view(), name="settings"),
    path("home/", HomePageView.as_view(), name="home"),
]
