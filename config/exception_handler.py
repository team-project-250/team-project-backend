"""Project-wide DRF exception handler.

DRF's default handler only produces a Response for Http404,
PermissionDenied and APIException subclasses — anything else (a bug, an
unexpected AttributeError, ...) falls through to Django's own error
handling, which returns an HTML page instead of JSON. That breaks every
API consumer's expectation of a JSON body and leaves no trace in the logs.

This wraps the default handler: known DRF exceptions are left untouched,
anything else is logged and turned into a small JSON 500 in production.
In development (DEBUG=True) unhandled exceptions are left to propagate
so Django's interactive debug page still shows up.
"""

import logging

from django.conf import settings
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """Wrap DRF's default exception handler with a logged, JSON fallback.

    Args:
        exc: The exception raised inside a view.
        context: DRF's exception context dict (has a ``"view"`` key with
            the view instance the exception was raised in).

    Returns:
        DRF's own ``Response`` for exceptions it already understands
        (``Http404``, ``PermissionDenied``, ``APIException`` subclasses).
        For anything else: ``None`` in development (so Django's debug page
        still shows up), or a ``Response({"detail": ...}, status=500)``
        outside DEBUG, after logging the exception.
    """
    response = drf_exception_handler(exc, context)
    if response is not None:
        return response

    if settings.DEBUG:
        return None

    logger.exception("Unhandled exception in %s", context["view"].__class__.__name__)
    return Response(
        {"detail": "Internal server error."},
        status=500,
    )
