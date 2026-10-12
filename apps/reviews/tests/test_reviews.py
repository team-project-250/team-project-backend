import datetime

import pytest
from django.core.exceptions import ValidationError
from django.core.management import call_command

from apps.reviews.models import Review

pytestmark = pytest.mark.django_db


@pytest.fixture
def reviews():
    Review.objects.create(
        author_name="Олена",
        rating=5,
        text="Чудово",
        published_on=datetime.date(2026, 8, 1),
        is_published=True,
    )
    Review.objects.create(
        author_name="Ігор",
        rating=4,
        text="Добре",
        published_on=datetime.date(2026, 9, 1),
        is_published=True,
    )
    Review.objects.create(
        author_name="Прихований",
        rating=1,
        text="...",
        published_on=datetime.date(2026, 9, 15),
        is_published=False,
    )


def test_only_published_returned_newest_first(client, reviews):
    results = client.get("/api/reviews/").json()["results"]
    assert [r["author_name"] for r in results] == ["Ігор", "Олена"]


def test_review_payload_shape(client, reviews):
    review = client.get("/api/reviews/").json()["results"][0]
    assert set(review) == {
        "id",
        "author_name",
        "avatar",
        "rating",
        "text",
        "published_on",
    }


def test_rating_out_of_range_rejected():
    review = Review(
        author_name="X",
        rating=6,
        text="x",
        published_on=datetime.date(2026, 1, 1),
    )
    with pytest.raises(ValidationError):
        review.full_clean()


def test_seed_fixture_loads():
    call_command("loaddata", "reviews", verbosity=0)
    assert Review.objects.filter(is_published=True).count() == 6
