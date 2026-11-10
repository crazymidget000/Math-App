import pytest
from django.db import connection


def test_home_page_loads(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Math Quest" in response.content


@pytest.mark.django_db
def test_database_is_postgres():
    assert connection.vendor == "postgresql"
