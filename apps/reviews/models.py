from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Review(models.Model):
    author_name = models.CharField(max_length=120)
    avatar = models.ImageField(upload_to="reviews/", blank=True)
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    text = models.TextField()
    published_on = models.DateField()
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-published_on", "-id"]
        verbose_name = "review"
        verbose_name_plural = "reviews"

    def __str__(self):
        return f"{self.author_name} ({self.rating}/5)"
