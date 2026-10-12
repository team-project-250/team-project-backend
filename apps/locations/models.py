from django.db import models


class City(models.Model):
    """A service city with its pickup point, shown in the header/footer
    city selector and used to scope equipment availability
    (``Equipment.available_cities``) and bookings (``Booking.city``)."""

    name = models.CharField(max_length=64, unique=True)
    slug = models.SlugField(max_length=64, unique=True)
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    order = models.PositiveSmallIntegerField(default=0)

    # Pickup point — shown in the header, footer and city selector.
    pickup_address = models.CharField(max_length=255, blank=True)
    pickup_phone = models.CharField(max_length=32, blank=True)
    working_hours = models.CharField(max_length=64, default="Пн-Нд: Цілодобово")

    class Meta:
        ordering = ["order", "name"]
        verbose_name = "city"
        verbose_name_plural = "cities"

    def __str__(self):
        """Return the city name, used e.g. in the Django admin list view."""
        return self.name

    def save(self, *args, **kwargs):
        """Save the city, demoting any other city currently flagged
        ``is_default`` so at most one city stays default.

        Args:
            *args: Forwarded to ``models.Model.save``.
            **kwargs: Forwarded to ``models.Model.save``.
        """
        if self.is_default:
            City.objects.filter(is_default=True).exclude(pk=self.pk).update(
                is_default=False
            )
        super().save(*args, **kwargs)
