from django.core.validators import MinValueValidator
from django.db import models

from apps.locations.models import City


class Category(models.Model):
    """A top-level equipment category (e.g. "Пилососи", "Пароочисники")
    used for catalog navigation and the ``?category=`` filter."""

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "name"]
        verbose_name = "category"
        verbose_name_plural = "categories"

    def __str__(self):
        """Return the category name, used in the Django admin list."""
        return self.name


class Equipment(models.Model):
    """A rentable piece of equipment: the core catalog/product-page entity.

    Availability is never stored here — it's always computed on demand
    from :class:`~apps.bookings.models.Booking` rows, see
    ``apps.catalog.services.equipment_availability``.
    """

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    sku = models.CharField("SKU / article", max_length=50, unique=True)
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="equipment"
    )
    short_description = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    price_per_day = models.DecimalField(
        max_digits=8, decimal_places=2, validators=[MinValueValidator(0)]
    )
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    is_popular = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    main_image = models.ImageField(upload_to="equipment/", blank=True)
    available_cities = models.ManyToManyField(
        City, related_name="equipment", blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-rating", "name"]
        verbose_name = "equipment"
        verbose_name_plural = "equipment"

    def __str__(self):
        """Return the equipment name, used in the Django admin list."""
        return self.name


class EquipmentImage(models.Model):
    """One ordered photo in an :class:`Equipment`'s product-page gallery."""

    equipment = models.ForeignKey(
        Equipment, on_delete=models.CASCADE, related_name="images"
    )
    image = models.ImageField(upload_to="equipment/gallery/")
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        """Return "<equipment name> — image <order>" for the admin list."""
        return f"{self.equipment.name} — image {self.order}"


class EquipmentSpec(models.Model):
    """One key/value technical specification row (e.g. "Потужність: 1400
    Вт") shown in the product page's "Характеристики" tab."""

    equipment = models.ForeignKey(
        Equipment, on_delete=models.CASCADE, related_name="specs"
    )
    label = models.CharField(max_length=100)
    value = models.CharField(max_length=150)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        """Return "<label>: <value>" for the admin list."""
        return f"{self.label}: {self.value}"


class EquipmentIncludedItem(models.Model):
    """One line of an :class:`Equipment`'s "what's included" list
    (e.g. a hose or an attachment that ships with the rental)."""

    equipment = models.ForeignKey(
        Equipment, on_delete=models.CASCADE, related_name="included_items"
    )
    name = models.CharField(max_length=150)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        """Return the item name, used in the Django admin list."""
        return self.name


class EquipmentBenefit(models.Model):
    """A short bullet point shown next to the price (e.g. "Оригінальна
    хімія та інструктаж у комплекті")."""

    equipment = models.ForeignKey(
        Equipment, on_delete=models.CASCADE, related_name="benefits"
    )
    text = models.CharField(max_length=200)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        """Return the benefit text, used in the Django admin list."""
        return self.text


class EquipmentBadge(models.Model):
    """Free-form marker shown on the product page (e.g. "Оригінал Karcher",
    "Хіт продажів"). Deliberately a flexible admin-edited list rather than
    fixed boolean fields — the mockup badges aren't a stable, known set.
    Availability ("Доступно" / "Заброньовано до…") is NOT one of these —
    it's always computed, never editable, see catalog.services.
    """

    equipment = models.ForeignKey(
        Equipment, on_delete=models.CASCADE, related_name="badges"
    )
    label = models.CharField(max_length=50)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        """Return the badge label, used in the Django admin list."""
        return self.label


class EquipmentUseCase(models.Model):
    """ "Техніка підходить для:" list under the product page's Опис tab.

    Distinct from EquipmentBenefit (short bullets next to the price) and
    from content.AboutFeature (generic, site-wide list on the home page):
    this one is specific to a single piece of equipment.
    """

    equipment = models.ForeignKey(
        Equipment, on_delete=models.CASCADE, related_name="suitable_for"
    )
    text = models.CharField(max_length=200)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        """Return the use-case text, used in the Django admin list."""
        return self.text
