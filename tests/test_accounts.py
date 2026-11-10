import pytest
from django.contrib.auth.models import User

from apps.accounts.models import Player

PASSWORD = "dragon-castle-42"


def signup_data(**overrides):
    data = {
        "username": "brave_kid",
        "password1": PASSWORD,
        "password2": PASSWORD,
        "hero": "princess",
    }
    data.update(overrides)
    return data


@pytest.fixture
def player():
    user = User.objects.create_user(username="existing", password=PASSWORD)
    return Player.objects.create(user=user, hero="prince")


@pytest.mark.django_db
class TestSignup:
    def test_page_has_no_email_field_and_grown_up_note(self, client):
        response = client.get("/accounts/signup/")
        assert response.status_code == 200
        content = response.content.decode()
        assert "email" not in content.lower()
        assert "Ask a grown-up to help you sign up." in content

    def test_creates_user_and_player_and_logs_in(self, client):
        response = client.post("/accounts/signup/", signup_data())
        assert response.status_code == 302
        assert response.url == "/play/"

        user = User.objects.get(username="brave_kid")
        assert user.email == ""
        assert user.player.hero == "princess"
        assert user.player.level == 1
        assert user.player.xp == 0
        assert user.player.coins == 0

        assert client.get("/play/").status_code == 200

    def test_requires_a_hero_choice(self, client):
        response = client.post("/accounts/signup/", signup_data(hero=""))
        assert response.status_code == 200
        assert not User.objects.filter(username="brave_kid").exists()

    def test_rejects_invalid_hero(self, client):
        client.post("/accounts/signup/", signup_data(hero="dragon"))
        assert not User.objects.filter(username="brave_kid").exists()

    def test_rejects_mismatched_passwords(self, client):
        client.post("/accounts/signup/", signup_data(password2="something-else-99"))
        assert not User.objects.filter(username="brave_kid").exists()

    def test_rejects_duplicate_username(self, client, player):
        client.post("/accounts/signup/", signup_data(username="existing"))
        assert User.objects.filter(username="existing").count() == 1
        assert Player.objects.count() == 1


@pytest.mark.django_db
class TestLoginLogout:
    def test_login_redirects_to_play(self, client, player):
        response = client.post("/accounts/login/", {"username": "existing", "password": PASSWORD})
        assert response.status_code == 302
        assert response.url == "/play/"

    def test_wrong_password_shows_error(self, client, player):
        response = client.post("/accounts/login/", {"username": "existing", "password": "nope"})
        assert response.status_code == 200
        assert "don't match" in response.content.decode()

    def test_logout_requires_post_and_logs_out(self, client, player):
        client.force_login(player.user)
        response = client.post("/accounts/logout/")
        assert response.status_code == 302
        assert response.url == "/"
        assert client.get("/play/").status_code == 302


@pytest.mark.django_db
class TestPlayPage:
    def test_logged_out_user_is_redirected_to_login(self, client):
        response = client.get("/play/")
        assert response.status_code == 302
        assert response.url == "/accounts/login/?next=/play/"

    def test_logged_in_player_sees_placeholder(self, client, player):
        client.force_login(player.user)
        response = client.get("/play/")
        assert response.status_code == 200
        assert "Welcome, existing!" in response.content.decode()
