import json

import httpx
import pytest
from django.contrib.auth.models import User
from django.test import Client

from apps.accounts.models import Player
from apps.game import services
from apps.game.models import Battle, Monster
from apps.tutor.client import OPENROUTER_URL, fallback_hint, request_hint
from apps.tutor.models import HintRequest
from apps.tutor.validate import validate_hint

VALID_HINT = {
    "encouragement": "Good try! You can do this.",
    "steps": ["Start at seven.", "Count on five more."],
    "strategy": "counting_on",
}


@pytest.fixture
def provider(settings, monkeypatch):
    settings.OPENROUTER_API_KEY = "test-only-credential"
    settings.OPENROUTER_MODEL = "test/model"
    settings.AI_TIMEOUT_SECONDS = "8"
    calls = []

    def install(body=None, error=None, status=200):
        def post(url, **kwargs):
            calls.append((url, kwargs))
            if error:
                raise error
            return httpx.Response(
                status,
                json=body
                if body is not None
                else {"choices": [{"message": {"content": json.dumps(VALID_HINT)}}]},
                request=httpx.Request("POST", url),
            )

        monkeypatch.setattr("apps.tutor.client.httpx.post", post)

    install()
    return calls, install


@pytest.fixture
def wrong_question(client, db):
    user = User.objects.create_user(username="wizard-hero", password="wizard-castle-42")
    Player.objects.create(user=user, hero="princess")
    client.force_login(user)
    battle = services.start_battle(user, Monster.objects.get(order=1).pk)
    question = battle.questions.get()
    question.operand_a, question.operand_b = 7, 5
    question.prompt, question.correct_answer = "7 + 5", 12
    question.save()
    services.answer_question(user, battle.pk, question.pk, 11)
    question.refresh_from_db()
    return question


def hint_url(question):
    return f"/battle/{question.battle_id}/hint/"


def test_validator_accepts_boundaries_and_keeps_only_display_fields():
    payload = {
        **VALID_HINT,
        "encouragement": "a" * 160,
        "steps": ["b" * 160] * 4,
        "untrusted_extra": "ignored",
    }
    hint = validate_hint(json.dumps(payload))
    assert hint == {key: payload[key] for key in VALID_HINT}


def test_deeply_nested_provider_json_is_rejected():
    with pytest.raises(ValueError):
        validate_hint("[" * 2000 + "0" + "]" * 2000)


@pytest.mark.parametrize(
    "content",
    [
        "not json",
        "[]",
        "null",
        "1",
        None,
        {"steps": []},
        json.dumps({}),
        json.dumps({**VALID_HINT, "encouragement": 1}),
        json.dumps({**VALID_HINT, "encouragement": " "}),
        json.dumps({**VALID_HINT, "encouragement": "a" * 161}),
        json.dumps({**VALID_HINT, "steps": "a step"}),
        json.dumps({**VALID_HINT, "steps": []}),
        json.dumps({**VALID_HINT, "steps": ["step"] * 5}),
        json.dumps({**VALID_HINT, "steps": [1]}),
        json.dumps({**VALID_HINT, "steps": [" "]}),
        json.dumps({**VALID_HINT, "steps": ["a" * 161]}),
        json.dumps({**VALID_HINT, "strategy": []}),
        json.dumps({**VALID_HINT, "strategy": "unknown"}),
    ],
)
def test_validator_rejects_invalid_shapes_and_bounds(content):
    with pytest.raises(ValueError):
        validate_hint(content)


def test_provider_request_uses_only_server_math_data(wrong_question, provider):
    calls, _ = provider
    wrong_question.prompt = "Untrusted free text must not be sent"
    hint, status = request_hint(wrong_question)
    assert (hint, status) == (VALID_HINT, "ok")
    url, request = calls[0]
    assert url == OPENROUTER_URL
    assert request["headers"] == {"Authorization": "Bearer test-only-credential"}
    assert request["timeout"] == 8
    assert request["json"]["model"] == "test/model"
    assert request["json"]["response_format"] == {"type": "json_object"}
    assert json.loads(request["json"]["messages"][1]["content"]) == {
        "a": 7,
        "b": 5,
        "operation": "add",
        "child_answer": 11,
    }


@pytest.mark.parametrize(
    "body",
    [
        [],
        "not an object",
        {},
        {"error": {"message": "provider error"}},
        {"choices": []},
        {"choices": "wrong"},
        {"choices": [None]},
        {"choices": [{"message": None}]},
        {"choices": [{"message": {}}]},
        {"choices": [{"message": {"content": None}}]},
        {"choices": [{"message": {"content": "not json"}}]},
        {"choices": [{"message": {"content": json.dumps({"steps": []})}}]},
    ],
)
def test_invalid_provider_responses_fall_back(wrong_question, provider, body):
    _, install = provider
    install(body=body)
    assert request_hint(wrong_question) == (fallback_hint("add"), "fallback")


@pytest.mark.parametrize("failure", ["timeout", "http", "malformed_body"])
def test_provider_failures_show_a_hint_not_errors(wrong_question, provider, failure, caplog):
    _, install = provider
    if failure == "timeout":
        install(error=httpx.ReadTimeout("do not expose test-only-credential"))
    elif failure == "http":
        install(status=401, body={"error": "do not expose test-only-credential"})
    else:

        def post(*args, **kwargs):
            return httpx.Response(
                200, text="not JSON", request=httpx.Request("POST", OPENROUTER_URL)
            )

        install()
        # A response body can be invalid JSON before its envelope is inspected.
        with pytest.MonkeyPatch.context() as patch:
            patch.setattr("apps.tutor.client.httpx.post", post)
            assert request_hint(wrong_question) == (fallback_hint("add"), "fallback")
        return
    assert request_hint(wrong_question) == (fallback_hint("add"), "fallback")
    assert "test-only-credential" not in caplog.text


@pytest.mark.parametrize("missing", ["OPENROUTER_API_KEY", "OPENROUTER_MODEL"])
def test_missing_config_skips_provider(wrong_question, provider, settings, missing):
    setattr(settings, missing, "")
    assert request_hint(wrong_question) == (fallback_hint("add"), "fallback")
    assert not provider[0]


@pytest.mark.parametrize("timeout", ["bad", "0", "-1", "nan", "inf"])
def test_invalid_timeout_falls_back(wrong_question, provider, settings, timeout):
    settings.AI_TIMEOUT_SECONDS = timeout
    assert request_hint(wrong_question) == (fallback_hint("add"), "fallback")
    assert not provider[0]


def test_wizard_targets_previous_wrong_question_and_caches_hint(client, wrong_question, provider):
    question = wrong_question
    battle = question.battle
    page = client.get(f"/battle/{battle.pk}/").content.decode()
    assert "Help with 7 + 5" in page and "Ask the Wizard" in page
    assert f'hx-target="#wizard-hint-{question.pk}"' in page
    assert f'name="question_id" value="{question.pk}"' in page
    before = list(Battle.objects.filter(pk=battle.pk).values())
    response = client.post(hint_url(question), {"question_id": question.pk}, HTTP_HX_REQUEST="true")
    assert response.status_code == 200
    html = response.content.decode()
    assert f'id="wizard-hint-{question.pk}"' in html
    assert 'id="battle-state"' not in html
    assert "Count on five more" in html and "Attack!" not in html
    assert "test-only-credential" not in html
    assert len(provider[0]) == 1
    assert HintRequest.objects.get(question=question).status == "ok"
    assert list(Battle.objects.filter(pk=battle.pk).values()) == before
    assert question.battle.questions.filter(answered_at=None).count() == 1

    response = client.post(hint_url(question), {"question_id": question.pk})
    assert response.status_code == 302
    assert response.url == f"/battle/{battle.pk}/#wizard-hint-{question.pk}"
    assert len(provider[0]) == 1
    reloaded = client.get(response.url).content.decode()
    assert "Count on five more" in reloaded
    assert "Ask the Wizard" not in reloaded


def test_stale_hint_response_is_only_for_its_original_question(client, wrong_question, provider):
    question = wrong_question
    next_question = question.battle.questions.get(answered_at=None)
    services.answer_question(
        question.battle.player.user,
        question.battle_id,
        next_question.pk,
        next_question.correct_answer,
    )
    state = list(Battle.objects.filter(pk=question.battle_id).values())
    response = client.post(hint_url(question), {"question_id": question.pk}, HTTP_HX_REQUEST="true")
    assert response.status_code == 200
    assert f'id="wizard-hint-{question.pk}"' in response.content.decode()
    assert "battle-state" not in response.content.decode()
    assert list(Battle.objects.filter(pk=question.battle_id).values()) == state
    assert "Ask the Wizard" not in client.get(f"/battle/{question.battle_id}/").content.decode()


def test_hint_endpoint_requires_owner_and_an_answered_wrong_question(
    client, wrong_question, provider
):
    question = wrong_question
    stranger = User.objects.create_user(username="other-wizard")
    Player.objects.create(user=stranger, hero="prince")
    other_battle = services.start_battle(stranger, Monster.objects.get(order=1).pk)
    unanswered = question.battle.questions.get(answered_at=None)
    assert client.get(hint_url(question)).status_code == 405
    assert (
        client.post(f"/battle/{other_battle.pk}/hint/", {"question_id": question.pk}).status_code
        == 404
    )
    assert client.post(hint_url(question), {"question_id": unanswered.pk}).status_code == 404
    assert (
        client.post(
            hint_url(question), {"question_id": other_battle.questions.get().pk}
        ).status_code
        == 404
    )
    question.is_correct = True
    question.save()
    assert client.post(hint_url(question), {"question_id": question.pk}).status_code == 404
    client.logout()
    assert client.post(hint_url(question), {"question_id": question.pk}).status_code == 302
    assert not provider[0] and not HintRequest.objects.exists()


@pytest.mark.parametrize("question_id", [None, "", "bad", "0", "-1", str(2**63)])
def test_invalid_question_id_is_a_bad_request(client, wrong_question, provider, question_id):
    data = {} if question_id is None else {"question_id": question_id}
    assert client.post(hint_url(wrong_question), data).status_code == 400
    assert not provider[0]


def test_hint_preserves_csrf_and_escapes_provider_text(wrong_question, provider):
    _, install = provider
    malicious = {**VALID_HINT, "steps": ["<script>alert('no')</script>"]}
    install(body={"choices": [{"message": {"content": json.dumps(malicious)}}]})
    browser = Client(enforce_csrf_checks=True)
    browser.force_login(wrong_question.battle.player.user)
    page = browser.get(f"/battle/{wrong_question.battle_id}/")
    assert (
        browser.post(hint_url(wrong_question), {"question_id": wrong_question.pk}).status_code
        == 403
    )
    token = browser.cookies["csrftoken"].value
    assert page.content.decode().count('name="csrfmiddlewaretoken"') >= 3
    response = browser.post(
        hint_url(wrong_question),
        {
            "question_id": wrong_question.pk,
            "csrfmiddlewaretoken": token,
        },
        follow=True,
    )
    assert response.status_code == 200
    html = response.content.decode()
    assert "&lt;script&gt;" in html and "<script>alert" not in html


def test_fallback_is_rendered_and_reused(client, wrong_question, provider):
    _, install = provider
    install(error=httpx.ConnectError("private provider failure"))
    response = client.post(
        hint_url(wrong_question), {"question_id": wrong_question.pk}, follow=True
    )
    html = response.content.decode()
    assert response.status_code == 200
    assert "Count on by the second number" in html
    assert "private provider failure" not in html
    assert HintRequest.objects.get(question=wrong_question).status == "fallback"
    client.post(hint_url(wrong_question), {"question_id": wrong_question.pk})
    assert len(provider[0]) == 1


@pytest.mark.parametrize("invalid_text", ["\x00", "\ud800"])
def test_nonstorable_provider_text_falls_back_before_database_save(
    client, wrong_question, provider, invalid_text
):
    _, install = provider
    data = {**VALID_HINT, "steps": [invalid_text]}
    install(body={"choices": [{"message": {"content": json.dumps(data)}}]})
    response = client.post(
        hint_url(wrong_question), {"question_id": wrong_question.pk}, HTTP_HX_REQUEST="true"
    )
    assert response.status_code == 200
    assert "Count on by the second number" in response.content.decode()
    assert HintRequest.objects.get(question=wrong_question).status == "fallback"
