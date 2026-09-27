from django.contrib import admin

from apps.reviews.models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    """Django admin configuration for :class:`~apps.reviews.models.Review`,
    including the moderation ("publish selected") bulk action."""

    list_display = ("author_name", "rating", "published_on", "is_published")
    list_filter = ("is_published", "rating")
    list_editable = ("is_published",)
    search_fields = ("author_name", "text")
    date_hierarchy = "published_on"
    actions = ["publish_selected"]

    @admin.action(description="Publish selected reviews")
    def publish_selected(self, request, queryset):
        """Mark the selected reviews ``is_published=True`` in bulk.

        Args:
            request: The current admin ``HttpRequest`` (used to display the
                confirmation message).
            queryset: The reviews selected in the admin changelist.
        """
        updated = queryset.update(is_published=True)
        self.message_user(request, f"{updated} review(s) published.")
