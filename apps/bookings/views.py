from drf_spectacular.utils import OpenApiParameter, extend_schema
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

_ERROR_DETAIL_SCHEMA = {
    "type": "object",
    "properties": {"detail": {"type": "string"}},
}


class BookingLookupThrottle(AnonRateThrottle):
    """Customers have no accounts — a phone number (lookup) or phone +
    booking number (cancel) is the only credential, so both endpoints are
    rate-limited to make enumeration / brute force impractical."""

    scope = "booking_lookup"
    rate = "30/hour"


class BookingCancelThrottle(AnonRateThrottle):
    """Rate-limits ``POST /api/bookings/{number}/cancel/`` — see
    :class:`BookingLookupThrottle`."""

    scope = "booking_cancel"
    rate = "10/hour"


class BookingCreateThrottle(AnonRateThrottle):
    """Creating a booking blocks real availability for its dates without any
    payment upfront (cash/transfer on pickup only) — with no accounts, an
    unthrottled create would let anyone spam junk bookings and lock
    equipment away from real customers."""

    scope = "booking_create"
    rate = "10/hour"


class BookingListCreateView(APIView):
    """``GET``/``POST /api/bookings/`` — look up a phone number's bookings,
    or create a new one. Public, unauthenticated."""

    permission_classes = [AllowAny]

    def get_throttles(self):
        """Pick the throttle for the current method.

        Returns:
            A single-item list: :class:`BookingLookupThrottle` for `GET`,
            :class:`BookingCreateThrottle` for `POST`.
        """
        if self.request.method == "GET":
            return [BookingLookupThrottle()]
        return [BookingCreateThrottle()]

    @extend_schema(
        summary="List a phone number's bookings",
        description="Returns that phone number's bookings, newest first.",
        parameters=[
            OpenApiParameter(
                "phone", str, required=True, description="Exact phone match."
            )
        ],
        responses={
            200: BookingSerializer(many=True),
            400: _ERROR_DETAIL_SCHEMA,
        },
        tags=["bookings"],
    )
    def get(self, request):
        """Serve ``GET /api/bookings/?phone=``.

        Args:
            request: The current request; must carry a `phone` query param.

        Returns:
            `200` with that phone number's bookings (newest first), or
            `400` if `phone` is missing.
        """
        phone = request.query_params.get("phone")
        if not phone:
            return Response(
                {"phone": ["This query parameter is required."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        bookings = get_bookings_by_phone(phone)
        return Response(BookingSerializer(bookings, many=True).data)

    @extend_schema(
        summary="Create a booking",
        description=(
            "Server computes the price and checks availability. Throttled "
            "to 10/hour per IP."
        ),
        request=BookingCreateSerializer,
        responses={
            201: BookingSerializer,
            400: _ERROR_DETAIL_SCHEMA,
            409: _ERROR_DETAIL_SCHEMA,
        },
        tags=["bookings"],
    )
    def post(self, request):
        """Serve ``POST /api/bookings/``.

        Args:
            request: The current request; body per
                :class:`~apps.bookings.serializers.BookingCreateSerializer`.

        Returns:
            `201` with the created booking, `400` for invalid input, or
            `409` if the equipment is already booked for those dates.
        """
        serializer = BookingCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            serializer.save()
        except EquipmentNotAvailableError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class BookingQuoteView(APIView):
    """``POST /api/bookings/quote/`` — price preview, no booking created.
    Public, unauthenticated, unthrottled (read-only, no side effects)."""

    permission_classes = [AllowAny]

    @extend_schema(
        summary="Preview a rental's price",
        description="No booking is created and availability isn't checked "
        "— only the date range's validity.",
        request=BookingQuoteSerializer,
        responses={200: BookingQuoteResponseSerializer, 400: _ERROR_DETAIL_SCHEMA},
        tags=["bookings"],
    )
    def post(self, request):
        """Serve ``POST /api/bookings/quote/``.

        Args:
            request: The current request; body per
                :class:`~apps.bookings.serializers.BookingQuoteSerializer`.

        Returns:
            `200` with the price breakdown, or `400` for an invalid date range.
        """
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
    """``POST /api/bookings/{number}/cancel/``. Public, unauthenticated —
    the request body's phone number must match the booking's own."""

    permission_classes = [AllowAny]
    throttle_classes = [BookingCancelThrottle]

    @extend_schema(
        summary="Cancel a booking",
        description="Only `pending`/`confirmed` bookings with a future "
        "start date can be cancelled. Throttled to 10/hour per IP.",
        request=BookingCancelSerializer,
        responses={
            200: BookingSerializer,
            400: _ERROR_DETAIL_SCHEMA,
            404: _ERROR_DETAIL_SCHEMA,
        },
        tags=["bookings"],
    )
    def post(self, request, number):
        """Serve ``POST /api/bookings/{number}/cancel/``.

        Args:
            request: The current request; body ``{"phone": "..."}``.
            number: The booking number from the URL (e.g. ``"ER-12345"``).

        Returns:
            `200` with the cancelled booking, `404` if the number/phone
            combination doesn't match any booking, or `400` if the booking
            is no longer eligible for cancellation.
        """
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
    """``POST /api/callback-requests/`` — the "1-click booking" lead form.
    Public, unauthenticated, throttled to 5/hour per IP."""

    permission_classes = [AllowAny]
    throttle_classes = [CallbackRequestThrottle]

    @extend_schema(
        summary="Submit a 1-click booking request",
        description=(
            "A lead for a manager to call back, not a real reservation. "
            "`200` (not `201`) is returned if an identical unprocessed "
            "request for the same phone + equipment already exists within "
            "the last few minutes."
        ),
        request=CallbackRequestSerializer,
        responses={
            200: CallbackRequestSerializer,
            201: CallbackRequestSerializer,
            400: _ERROR_DETAIL_SCHEMA,
            409: _ERROR_DETAIL_SCHEMA,
        },
        tags=["bookings"],
    )
    def post(self, request):
        """Serve ``POST /api/callback-requests/``.

        Args:
            request: The current request; body per
                :class:`~apps.bookings.serializers.CallbackRequestSerializer`.

        Returns:
            `201` for a new request, `200` for a detected duplicate, `400`
            for bad phone/dates, or `409` for a date conflict on the given
            equipment.
        """
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
