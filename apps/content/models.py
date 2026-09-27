"""Editable content for the home page — no hardcoded copy on the frontend.

HeroSection, AboutSection and SiteSettings are singletons: save() forces
pk=1 so a second row can never be created (even from a shell or fixture),
and the admin additionally hides the "Add" button once a row exists
(see content/admin.py). load() returns the single row, creating a blank
one on first access so an empty database never 500s the API.
"""

from django.db import models


class HeroSection(models.Model):
    """Singleton: the home page hero (title, subtitle, CTA, background
    image), editable in the admin. Use :meth:`load` to fetch it, never
    ``objects.get``/``.first()``."""

    title = models.CharField(max_length=200, blank=True, default="")
    subtitle = models.TextField(blank=True, default="")
    cta_label = models.CharField(max_length=60, blank=True, default="")
    cta_url = models.CharField(max_length=200, blank=True, default="")
    background_image = models.ImageField(upload_to="content/", blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "hero section"
        verbose_name_plural = "hero section"

    def __str__(self):
        """Return the hero title, or a placeholder if it's still blank."""
        return self.title or "Hero section"

    def save(self, *args, **kwargs):
        """Save the singleton row, always forcing ``pk=1``.

        Args:
            *args: Forwarded to ``models.Model.save``.
            **kwargs: Forwarded to ``models.Model.save``.
        """
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls) -> "HeroSection":
        """Fetch the singleton row, creating a blank one if none exists yet.

        Returns:
            The single :class:`HeroSection` instance.
        """
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class AboutSection(models.Model):
    """Singleton: the home page "About EasyRent" section, editable in the
    admin, with an ordered list of :class:`AboutFeature` items."""

    title = models.CharField(max_length=200, blank=True, default="")
    description = models.TextField(blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "about section"
        verbose_name_plural = "about section"

    def __str__(self):
        """Return the section title, or a placeholder if it's still blank."""
        return self.title or "About section"

    def save(self, *args, **kwargs):
        """Save the singleton row, always forcing ``pk=1``.

        Args:
            *args: Forwarded to ``models.Model.save``.
            **kwargs: Forwarded to ``models.Model.save``.
        """
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls) -> "AboutSection":
        """Fetch the singleton row, creating a blank one if none exists yet.

        Returns:
            The single :class:`AboutSection` instance.
        """
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class AboutFeature(models.Model):
    """One bullet point in the home page's "About EasyRent" feature list."""

    about = models.ForeignKey(
        AboutSection, on_delete=models.CASCADE, related_name="features"
    )
    icon = models.CharField(max_length=50, blank=True)
    text = models.CharField(max_length=200)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        """Return the feature text, used in the Django admin list."""
        return self.text


class RentalStep(models.Model):
    """One step in the home page's "How to rent" list (e.g. "1. Обери
    техніку")."""

    order = models.PositiveSmallIntegerField(default=0)
    icon = models.CharField(max_length=50, blank=True)
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        """Return the step title, used in the Django admin list."""
        return self.title


class RentalTerm(models.Model):
    """One card in the home page's "Rental terms" list (e.g. delivery,
    payment methods, minimum rental period)."""

    order = models.PositiveSmallIntegerField(default=0)
    icon = models.CharField(max_length=50, blank=True)
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        """Return the term title, used in the Django admin list."""
        return self.title


class DeliveryPaymentInfo(models.Model):
    """Singleton: the "Доставка і оплата" tab on the product page — global
    text, same for every product (delivery/payment terms don't vary per
    item)."""

    title = models.CharField(max_length=200, blank=True, default="")
    description = models.TextField(blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "delivery & payment info"
        verbose_name_plural = "delivery & payment info"

    def __str__(self):
        """Return the title, or a placeholder if it's still blank."""
        return self.title or "Delivery & payment info"

    def save(self, *args, **kwargs):
        """Save the singleton row, always forcing ``pk=1``.

        Args:
            *args: Forwarded to ``models.Model.save``.
            **kwargs: Forwarded to ``models.Model.save``.
        """
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls) -> "DeliveryPaymentInfo":
        """Fetch the singleton row, creating a blank one if none exists yet.

        Returns:
            The single :class:`DeliveryPaymentInfo` instance.
        """
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class SiteSettings(models.Model):
    """Singleton: company/bank details shown after a customer picks the
    IBAN-transfer payment method."""

    company_name = models.CharField(max_length=150, blank=True, default="")
    bank_name = models.CharField(max_length=150, blank=True, default="")
    iban = models.CharField(max_length=40, blank=True, default="")
    recipient_name = models.CharField(max_length=150, blank=True, default="")
    edrpou = models.CharField("ЄДРПОУ / ІПН", max_length=20, blank=True, default="")
    transfer_note = models.TextField(blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "site settings"
        verbose_name_plural = "site settings"

    def __str__(self):
        """Return a fixed label, since there's only ever one row."""
        return "Site settings"

    def save(self, *args, **kwargs):
        """Save the singleton row, always forcing ``pk=1``.

        Args:
            *args: Forwarded to ``models.Model.save``.
            **kwargs: Forwarded to ``models.Model.save``.
        """
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls) -> "SiteSettings":
        """Fetch the singleton row, creating a blank one if none exists yet.

        Returns:
            The single :class:`SiteSettings` instance.
        """
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
