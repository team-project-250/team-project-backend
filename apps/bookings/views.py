from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from apps.bookings.serializers import (
    BookingCancelSerializer,
    BookingCreateSerializer,
    BookingQuoteResponseSerializer,
    BookingQuoteSerializer,
    BookingSerializer,
    CallbackRequestSerializer,
)
from apps.bookings.services import (
    BookingNotCancellableError,
    BookingNotFoundError,
    EquipmentNotAvailableError,
    InvalidDateRangeError,
    cancel_booking,
    get_bookings_by_phone,
    quote_price,
    submit_callback_request,
)


class BookingLookupThrottle(AnonRateThrottle):
    """Customers have no accounts — a phone number (lookup) or phone +
    booking number (cancel) is the only credential, so both endpoints are
    rate-limited to make enumeration / brute force impractical."""

    scope = "booking_lookup"
    rate = "30/hour"


class BookingCancelThrottle(AnonRateThrottle):
    scope = "booking_cancel"
    rate = "10/hour"


class BookingListCreateView(APIView):
    permission_classes = [AllowAny]

    def get_throttles(self):
        # Only the lookup is sensitive; creating a booking isn't throttled.
        if self.request.method == "GET":
            return [BookingLookupThrottle()]
        return super().get_throttles()

    def get(self, request):
        phone = request.query_params.get("phone")
        if not phone:
            return Response(
                {"phone": ["This query parameter is required."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        bookings = get_bookings_by_phone(phone)
        return Response(BookingSerializer(bookings, many=True).data)

    def post(self, request):
        serializer = BookingCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            serializer.save()
        except EquipmentNotAvailableError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class BookingQuoteView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = BookingQuoteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        pricing = quote_price(
            equipment=data["equipment"],
            start_date=data["start_date"],
            end_date=data["end_date"],
            delivery_method=data["delivery_method"],
        )
        return Response(BookingQuoteResponseSerializer(pricing).data)


class BookingCancelView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [BookingCancelThrottle]

    def post(self, request, number):
        serializer = BookingCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            booking = cancel_booking(
                number=number, phone=serializer.validated_data["phone"]
            )
        except BookingNotFoundError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        except BookingNotCancellableError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(BookingSerializer(booking).data)


class CallbackRequestThrottle(AnonRateThrottle):
    """Scoped to this one public write endpoint — deliberately not part of
    the project-wide throttling setup (there isn't one yet, see the
    roadmap's hardening milestone); this is a small, self-contained guard
    against spamming the "1-click" form, not that infrastructure."""

    scope = "callback_request"
    rate = "5/hour"


class CallbackRequestCreateView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [CallbackRequestThrottle]

    def post(self, request):
        serializer = CallbackRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            callback_request, created = submit_callback_request(
                **serializer.validated_data
            )
        except InvalidDateRangeError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except EquipmentNotAvailableError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)

        response_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(
            CallbackRequestSerializer(callback_request).data, status=response_status
        )
