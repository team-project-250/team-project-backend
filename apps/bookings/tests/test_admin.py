"""Smoke tests for the bookings admin — catches crashes like a stray '%'
in an admin action description breaking the whole changelist page.
"""

import pytest

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin_client(client, django_user_model):
    user = django_user_model.objects.create_superuser(
        username="admin", email="admin@example.com", password="pass"
    )
    client.force_login(user)
    return client


def test_booking_changelist_renders(admin_client):
    response = admin_client.get("/admin/bookings/booking/")
    assert response.status_code == 200


def test_callback_request_changelist_renders(admin_client):
    response = admin_client.get("/admin/bookings/callbackrequest/")
    assert response.status_code == 200
