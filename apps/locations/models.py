from django.db import models


class City(models.Model):
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
        return self.name

    def save(self, *args, **kwargs):
        # Keep exactly one default city.
        if self.is_default:
            City.objects.filter(is_default=True).exclude(pk=self.pk).update(
                is_default=False
            )
        super().save(*args, **kwargs)
