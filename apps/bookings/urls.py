"""Bookings API routes."""

from django.urls import path

from apps.bookings.views import (
    BookingCancelView,
    BookingListCreateView,
    BookingQuoteView,
    CallbackRequestCreateView,
)

app_name = "bookings"

urlpatterns = [
    path("bookings/", BookingListCreateView.as_view(), name="booking-list-create"),
    path("bookings/quote/", BookingQuoteView.as_view(), name="booking-quote"),
    path(
        "bookings/<str:number>/cancel/",
        BookingCancelView.as_view(),
        name="booking-cancel",
    ),
    path(
        "callback-requests/",
        CallbackRequestCreateView.as_view(),
        name="callback-request-create",
    ),
]
