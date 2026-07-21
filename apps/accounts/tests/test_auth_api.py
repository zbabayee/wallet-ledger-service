import pytest

from django.urls import reverse
from rest_framework_simplejwt.exceptions import TokenError


from django.contrib.auth import get_user_model


User = get_user_model()


@pytest.mark.django_db
class TestAuthenticationAPI:

    def test_register_success(self, api_client):
        response = api_client.post(
            reverse("register"),
            {
                "username": "zhr",
                "email": "test@test.com",
                "password": "Pss_zhr@@123",
                "password_confirm": "Pss_zhr@@123",
                "mobile": "09130650480",
                "first_name":"zahra",
                "last_name":"test",
            },
            format="json",
        )
        print(response.status_code)
        print(response.data)
        assert response.status_code == 201
        assert response.data["user"]["username"] == "zhr"
        assert "access" in response.data["tokens"]
        assert "refresh" in response.data["tokens"]
        assert User.objects.filter(username="zhr").exists()


    def test_register_validation_error(self, api_client):
        response = api_client.post(
            reverse("register"),
            {},
            format="json",
        )
        assert response.status_code == 400


    def test_login_success(
        self,
        api_client,
        user,
    ):
        response = api_client.post(
            reverse("login"),
            {
                "username": user.username,
                "password": "Password123",
            },
            format="json",
        )

        assert response.status_code == 200
        assert "access" in response.data["tokens"]
        assert "refresh" in response.data["tokens"]
        user.refresh_from_db()
        assert user.last_login is not None



    def test_login_wrong_password(
        self,
        api_client,
        user,
    ):

        response = api_client.post(
            reverse("login"),
            {
                "username": user.username,
                "password": "wrong-password",
            },
            format="json",
        )
        assert response.status_code == 400



    def test_logout_success(
        self,
        api_client,
        user,
    ):
        from rest_framework_simplejwt.tokens import RefreshToken

        refresh = RefreshToken.for_user(user)
        api_client.force_authenticate(user=user)
        response = api_client.post(
            reverse("logout"),
            {
                "refresh": str(refresh),
            },
            format="json",
        )
        assert response.status_code == 200
        assert response.data["message"] == (
            "Successfully logged out"
        )
        with pytest.raises(TokenError):
            RefreshToken(str(refresh))



    def test_logout_invalid_token(
        self,
        api_client,
        user,
    ):

        api_client.force_authenticate(user=user)
        response = api_client.post(
            reverse("logout"),
            {
                "refresh": "invalid-token",
            },
            format="json",
        )
        assert response.status_code == 400