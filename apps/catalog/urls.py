"""Catalog API routes."""

from rest_framework.routers import DefaultRouter

from apps.catalog.views import CategoryViewSet, EquipmentViewSet

app_name = "catalog"

router = DefaultRouter()
router.register("categories", CategoryViewSet, basename="category")
router.register("equipment", EquipmentViewSet, basename="equipment")

urlpatterns = router.urls
