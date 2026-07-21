import pytest
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.api.serializers import UserSerializer
from common.tools import get_client_ip

User = get_user_model()


class UserService:
    @staticmethod
    @transaction.atomic
    def register_user(validated_data):
        validated_data.pop("password_confirm", None)

        user = User.objects.create_user(
            **validated_data)
        refresh = RefreshToken.for_user(user)
        return {
            "user": UserSerializer(user).data,
            "tokens": {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            }
        }


class AuthService:
    @staticmethod
    def login_user(user, request):
        """
        Handle user login business logic.
        Update login information and generate JWT tokens.
        """
        user.last_login = timezone.now()
        user.save(
            update_fields=[
                "last_login",
            ]
        )
        refresh = RefreshToken.for_user(user)
        return {
            "user": UserSerializer(user).data,
            "tokens": {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            }
        }

    @staticmethod
    def logout_user(refresh_token):
        """
        Blacklist refresh token using SimpleJWT.
        """
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except TokenError:
            raise ValueError("Invalid Token")
        return {
            "message": "Successfully logged out"
        }


