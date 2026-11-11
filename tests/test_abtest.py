from uuid import uuid4

import pytest
from django.test import Client
from django.utils import timezone

from apps.abtest.models import ABVisitor

PAGE = "/f48c8ec"
CLICK = f"{PAGE}/click"
STATS = f"{PAGE}/stats"

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("variant", ["kudos", "thanks"])
def test_public_page_assigns_one_persistent_variant(client, settings, monkeypatch, variant):
    settings.AB_TEST_TEAM_NICKNAMES = ["example-one", "example-two"]
    monkeypatch.setattr("apps.abtest.views.choice", lambda variants: variant)

    response = client.get(PAGE)

    assert response.status_code == 200
    assert b"example-one, example-two" in response.content
    assert response.content.count(b'id="abtest"') == 1
    assert f">{variant}</button>".encode() in response.content
    assert response.cookies["ab_vid"]["httponly"]
    assert response.cookies["ab_vid"]["samesite"] == "Lax"
    assert "no-store" in response.headers["Cache-Control"]

    visitor = ABVisitor.objects.get()
    assert visitor.variant == variant
    assert visitor.impression_at is not None
    assert client.get(PAGE).content.count(f">{variant}</button>".encode()) == 1
    assert ABVisitor.objects.count() == 1

    Client().get(PAGE)
    assert ABVisitor.objects.count() == 2


def test_click_requires_csrf_and_only_counts_once():
    client = Client(enforce_csrf_checks=True)
    client.get(PAGE)
    visitor = ABVisitor.objects.get()

    assert client.get(CLICK).status_code == 405
    assert client.post(CLICK).status_code == 403
    visitor.refresh_from_db()
    assert visitor.clicked_at is None

    form_data = {"csrfmiddlewaretoken": client.cookies["csrftoken"].value}
    response = client.post(CLICK, form_data, follow=True)

    assert response.redirect_chain == [(PAGE, 303)]
    assert f">{visitor.variant}</button>".encode() in response.content
    visitor.refresh_from_db()
    first_click = visitor.clicked_at
    assert first_click is not None

    assert client.post(CLICK, form_data).status_code == 303
    visitor.refresh_from_db()
    assert visitor.clicked_at == first_click
    assert ABVisitor.objects.count() == 1


@pytest.mark.parametrize("cookie", [None, "invalid-uuid", str(uuid4())])
def test_click_without_known_visitor_does_not_count(client, cookie):
    if cookie is not None:
        client.cookies["ab_vid"] = cookie

    response = client.post(CLICK)

    assert response.status_code == 303
    assert response.headers["Location"] == PAGE
    assert not ABVisitor.objects.exists()
    assert client.get(PAGE).status_code == 200
    assert ABVisitor.objects.count() == 1


def test_stats_returns_zero_counts_before_any_visits(client):
    response = client.get(STATS)

    assert response.status_code == 200
    assert response.json() == {
        "preferred": "kudos",
        "kudos": {"impressions": 0, "clicks": 0},
        "thanks": {"impressions": 0, "clicks": 0},
    }
    assert not ABVisitor.objects.exists()


def test_stats_uses_click_through_rate_and_breaks_ties_with_kudos(client):
    now = timezone.now()
    ABVisitor.objects.bulk_create(
        [
            ABVisitor(variant="kudos", clicked_at=now),
            ABVisitor(variant="kudos", clicked_at=now),
            ABVisitor(variant="kudos"),
            ABVisitor(variant="kudos"),
            ABVisitor(variant="thanks", clicked_at=now),
        ]
    )

    assert client.get(STATS).json() == {
        "preferred": "thanks",
        "kudos": {"impressions": 4, "clicks": 2},
        "thanks": {"impressions": 1, "clicks": 1},
    }

    ABVisitor.objects.create(variant="thanks")
    assert client.get(STATS).json()["preferred"] == "kudos"
