import pytest

from apps.content.models import (
    AboutFeature,
    AboutSection,
    DeliveryPaymentInfo,
    HeroSection,
    RentalStep,
    RentalTerm,
    SiteSettings,
)

pytestmark = pytest.mark.django_db


def test_hero_self_heals_on_empty_db(client):
    assert HeroSection.objects.count() == 0
    response = client.get("/api/content/hero/")
    assert response.status_code == 200
    assert response.json() == {
        "title": "",
        "subtitle": "",
        "cta_label": "",
        "cta_url": "",
        "background_image": None,
    }


def test_hero_returns_the_singleton_content(client):
    HeroSection.objects.create(
        title="Оренда професійної техніки",
        subtitle="Швидко та якісно",
        cta_label="Обрати техніку",
        cta_url="/catalog",
    )
    data = client.get("/api/content/hero/").json()
    assert data["title"] == "Оренда професійної техніки"
    assert data["cta_url"] == "/catalog"


def test_about_includes_ordered_features(client):
    about = AboutSection.objects.create(title="Про сервіс", description="...")
    AboutFeature.objects.create(about=about, text="Другий", order=2)
    AboutFeature.objects.create(about=about, text="Перший", order=1)

    data = client.get("/api/content/about/").json()
    assert [f["text"] for f in data["features"]] == ["Перший", "Другий"]


def test_rental_steps_excludes_inactive_and_orders(client):
    RentalStep.objects.create(title="Крок 2", order=2)
    RentalStep.objects.create(title="Крок 1", order=1)
    RentalStep.objects.create(title="Прихований", order=0, is_active=False)

    data = client.get("/api/content/rental-steps/").json()
    assert [s["title"] for s in data] == ["Крок 1", "Крок 2"]


def test_rental_terms_excludes_inactive_and_orders(client):
    RentalTerm.objects.create(title="Умова 2", order=2)
    RentalTerm.objects.create(title="Умова 1", order=1)
    RentalTerm.objects.create(title="Прихована", order=0, is_active=False)

    data = client.get("/api/content/rental-terms/").json()
    assert [t["title"] for t in data] == ["Умова 1", "Умова 2"]


def test_delivery_payment_self_heals_on_empty_db(client):
    assert DeliveryPaymentInfo.objects.count() == 0
    response = client.get("/api/content/delivery-payment/")
    assert response.status_code == 200
    assert response.json() == {"title": "", "description": ""}


def test_delivery_payment_returns_content(client):
    DeliveryPaymentInfo.objects.create(
        title="Доставка і оплата",
        description="Оплата здійснюється тільки при отриманні техніки.",
    )
    data = client.get("/api/content/delivery-payment/").json()
    assert data["title"] == "Доставка і оплата"


def test_settings_returns_transfer_details(client):
    SiteSettings.objects.create(
        company_name="EasyRent",
        iban="UA000000000000000000000000000",
        bank_name="Приватбанк",
    )
    data = client.get("/api/content/settings/").json()
    assert data["company_name"] == "EasyRent"
    assert data["iban"] == "UA000000000000000000000000000"
