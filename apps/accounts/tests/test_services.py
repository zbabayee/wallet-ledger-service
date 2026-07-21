import pytest
from django.contrib.auth import get_user_model

from apps.accounts.services.user_services import (
    UserService,
    AuthService,
)

User = get_user_model()


@pytest.mark.django_db
class TestUserService:

    def test_register_user_creates_user_and_returns_tokens(self):
        data = {
            "username": "zahra",
            "email": "test@test.com",
            "password": "StrongPassword123",
        }
        result = UserService.register_user(data)
        user = User.objects.get(username="zahra")
        assert user.email == "test@test.com"
        assert result["user"]["username"] == "zahra"
        assert "access" in result["tokens"]
        assert "refresh" in result["tokens"]

    def test_register_user_creates_active_user(self):
        data = {
            "username": "testuser",
            "password": "Password123",
        }
        UserService.register_user(data)
        user = User.objects.get(username="testuser")
        assert user.is_active is True


@pytest.mark.django_db
class TestAuthService:

    def test_login_generates_jwt_tokens(
            self,
            user,
            rf,
    ):
        request = rf.post(
            "/api/accounts/login/")
        request.META["REMOTE_ADDR"] = ("127.0.0.1")
        result = AuthService.login_user(
            user=user,
            request=request,
        )
        assert "tokens" in result
        assert "access" in result["tokens"]
        assert "refresh" in result["tokens"]
        user.refresh_from_db()
        assert user.last_login is not None


    def test_login_returns_serialized_user(
            self,
            user,
            rf,
    ):
        request = rf.post("/login/")
        result = AuthService.login_user(
            user,
            request,
        )
        assert result["user"]["username"] == (user.username)

    def test_logout_blacklists_refresh_token(self, user):
        from rest_framework_simplejwt.tokens import RefreshToken
        from rest_framework_simplejwt.exceptions import TokenError

        refresh = RefreshToken.for_user(user)
        result = AuthService.logout_user(
            str(refresh))
        assert result["message"] == ("Successfully logged out")
        with pytest.raises(TokenError):
            RefreshToken(str(refresh)).verify()

    def test_logout_rejects_invalid_token(self):
        with pytest.raises(
                ValueError
        ):
            AuthService.logout_user("invalid-token")
