"""Equipment availability — derived from bookings, never stored on Equipment.

catalog depends on bookings here (a one-off exception to the usual
direction): "чи доступна ця техніка" is fundamentally catalog's
concern, but the answer only exists in booking data. bookings.models
already depends on catalog.models (Equipment FK) — this doesn't create
an import cycle since it's a runtime service import, not a model one.
"""

from collections import defaultdict
from datetime import date, timedelta

from apps.bookings.models import Booking
from apps.catalog.models import Equipment


def _availability(bookings, on_date: date) -> dict:
    """Availability on `on_date` given an equipment's active bookings that
    end on or after it. Back-to-back bookings are chained, so
    `available_from` is the first day actually free — not just the day
    after whichever booking happens to cover `on_date`."""
    free_from = on_date
    for booking in sorted(bookings, key=lambda b: b.start_date):
        if booking.start_date > free_from:
            break
        free_from = max(free_from, booking.end_date + timedelta(days=1))
    if free_from == on_date:
        return {"status": "available", "available_from": None}
    return {"status": "booked", "available_from": free_from}


def _active_bookings_from(on_date: date):
    return Booking.objects.filter(
        status__in=Booking.ACTIVE_STATUSES, end_date__gte=on_date
    )


def equipment_availability(equipment: Equipment, on_date: date) -> dict:
    return _availability(
        _active_bookings_from(on_date).filter(equipment=equipment), on_date
    )


def annotate_availability(equipment_list, on_date: date) -> None:
    """Attach `.availability` to each Equipment instance with ONE query
    (instead of calling equipment_availability() per item — avoids N+1
    on the catalog list endpoint)."""
    bookings_by_equipment: dict[int, list[Booking]] = defaultdict(list)
    bookings = _active_bookings_from(on_date).filter(
        equipment_id__in=[item.pk for item in equipment_list]
    )
    for booking in bookings:
        bookings_by_equipment[booking.equipment_id].append(booking)

    for item in equipment_list:
        item.availability = _availability(bookings_by_equipment[item.pk], on_date)


def related_equipment(equipment: Equipment, limit: int = 3) -> list[Equipment]:
    """Equipment for the "Інша техніка" carousel: same category first
    (best match), then top up with other active equipment if the
    category doesn't have enough on its own. Never includes `equipment`
    itself."""
    base_qs = (
        Equipment.objects.filter(is_active=True)
        .exclude(pk=equipment.pk)
        .select_related("category")
    )

    same_category = list(base_qs.filter(category=equipment.category)[:limit])
    if len(same_category) >= limit:
        return same_category

    remaining = limit - len(same_category)
    other_ids = [item.pk for item in same_category]
    fillers = list(
        base_qs.exclude(category=equipment.category).exclude(pk__in=other_ids)[
            :remaining
        ]
    )
    return same_category + fillers
