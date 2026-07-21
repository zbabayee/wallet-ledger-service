import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="zahra",
        email="zahra@test.com",
        password="Password123",
        mobile="09130650476"
    )

@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(
        username="admin",
        email="admin@test.com",
        password="Password123",
        mobile="09130650477"
    )

@pytest.fixture
def another_user(db):
    return User.objects.create_user(
        username="ali",
        password="Password123",
        mobile="09130650478",
        email = "another@test.com",

    )