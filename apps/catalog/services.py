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
    """Compute availability on `on_date` from an equipment's own bookings.

    Back-to-back bookings are chained, so `available_from` is the first
    day actually free — not just the day after whichever booking happens
    to cover `on_date`.

    Args:
        bookings: An iterable of :class:`~apps.bookings.models.Booking`
            instances for a single piece of equipment (active status,
            ending on or after `on_date` — see :func:`_active_bookings_from`).
        on_date: The date to check availability for.

    Returns:
        ``{"status": "available", "available_from": None}`` or
        ``{"status": "booked", "available_from": date}`` where the date is
        the first day the equipment is free again.
    """
    free_from = on_date
    for booking in sorted(bookings, key=lambda b: b.start_date):
        if booking.start_date > free_from:
            break
        free_from = max(free_from, booking.end_date + timedelta(days=1))
    if free_from == on_date:
        return {"status": "available", "available_from": None}
    return {"status": "booked", "available_from": free_from}


def _active_bookings_from(on_date: date):
    """Return active bookings that could still block availability on or
    after `on_date` (i.e. haven't ended before it).

    Args:
        on_date: The date availability is being computed for.

    Returns:
        A ``QuerySet`` of :class:`~apps.bookings.models.Booking` with an
        active status (see ``Booking.ACTIVE_STATUSES``) and
        ``end_date >= on_date``, for any equipment (callers filter further).
    """
    return Booking.objects.filter(
        status__in=Booking.ACTIVE_STATUSES, end_date__gte=on_date
    )


def equipment_availability(equipment: Equipment, on_date: date) -> dict:
    """Compute one equipment's availability on a given date.

    Args:
        equipment: The equipment to check.
        on_date: The date to check availability for.

    Returns:
        See :func:`_availability`.
    """
    return _availability(
        _active_bookings_from(on_date).filter(equipment=equipment), on_date
    )


def annotate_availability(equipment_list, on_date: date) -> None:
    """Attach `.availability` to each Equipment instance with ONE query
    (instead of calling equipment_availability() per item — avoids N+1
    on the catalog list endpoint).

    Args:
        equipment_list: An iterable of :class:`~apps.catalog.models.Equipment`
            instances to annotate in place.
        on_date: The date to compute availability for.

    Returns:
        None. Each item in `equipment_list` gets an `.availability`
        attribute set to the dict described in :func:`_availability`.
    """
    bookings_by_equipment: dict[int, list[Booking]] = defaultdict(list)
    bookings = _active_bookings_from(on_date).filter(
        equipment_id__in=[item.pk for item in equipment_list]
    )
    for booking in bookings:
        bookings_by_equipment[booking.equipment_id].append(booking)

    for item in equipment_list:
        item.availability = _availability(bookings_by_equipment[item.pk], on_date)


def related_equipment(equipment: Equipment, limit: int = 3) -> list[Equipment]:
    """Pick equipment for the "Інша техніка" carousel: same category first
    (best match), then top up with other active equipment if the
    category doesn't have enough on its own. Never includes `equipment`
    itself.

    Args:
        equipment: The equipment being viewed, to find related items for.
        limit: Maximum number of items to return.

    Returns:
        A list of up to `limit` active :class:`~apps.catalog.models.Equipment`
        instances, same-category items first.
    """
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
