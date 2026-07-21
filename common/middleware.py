from urllib.parse import parse_qs
from channels.middleware import BaseMiddleware
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import (
    InvalidToken,
    TokenError,
)

from channels.db import database_sync_to_async

@database_sync_to_async
def get_user_from_token(token):
    from django.contrib.auth.models import AnonymousUser
    jwt_auth = JWTAuthentication()
    try:
        validated_token = jwt_auth.get_validated_token(token)
        return jwt_auth.get_user(validated_token)
    except (InvalidToken,TokenError):
        return AnonymousUser()



class JWTAuthMiddleware(BaseMiddleware):

    async def __call__(
        self,scope,
        receive,
        send,
    ):
        query_string = parse_qs(
            scope["query_string"].decode()
        )
        token = query_string.get("token")
        if token:
            scope["user"] = await get_user_from_token(token[0])
        else:
            from django.contrib.auth.models import AnonymousUser
            scope["user"] = AnonymousUser()
        return await super().__call__(
            scope,
            receive,
            send,
        )