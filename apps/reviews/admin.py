from django.contrib import admin

from apps.reviews.models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("author_name", "rating", "published_on", "is_published")
    list_filter = ("is_published", "rating")
    list_editable = ("is_published",)
    search_fields = ("author_name", "text")
    date_hierarchy = "published_on"
    actions = ["publish_selected"]

    @admin.action(description="Publish selected reviews")
    def publish_selected(self, request, queryset):
        updated = queryset.update(is_published=True)
        self.message_user(request, f"{updated} review(s) published.")
