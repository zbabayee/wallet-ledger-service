from decimal import Decimal

import pytest
from asgiref.sync import sync_to_async
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

from apps.transactions.services.transaction_service import transfer
from apps.wallets.models import Wallet, Currency
from config.asgi import application

User = get_user_model()


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestWalletNotificationConsumer:
    async def test_wallet_notification_after_transfer(self):
        """
        Receiver should get websocket notification
        after successful transfer.
        """
        sender = await self.create_user(username="sender", email="sender@gmail.com", mobile="09130650455")
        receiver = await self.create_user(username="receiver", email="receiver@gmail.com", mobile="09130650459")
        currency = await self.create_currency(code="USD")

        sender_wallet = await self.create_wallet(
            user=sender,
            currency=currency,
            balance=Decimal("5000")
        )
        receiver_wallet = await self.create_wallet(
            user=receiver,
            currency=currency,
            balance=Decimal("100")
        )
        token = await self.get_access_token(receiver)
        communicator = WebsocketCommunicator(
            application,
            f"/ws/notifications/?token={token}"
        )
        connected, _ = await communicator.connect()
        assert connected
        await self.execute_transfer(
            sender,
            sender_wallet.id,
            receiver_wallet.id
        )
        message = await communicator.receive_json_from(timeout=5)
        assert message["amount"] == "500"
        assert message["currency"] == "USD"
        assert (message["message"] == "You received 500 USD")
        await communicator.disconnect()

    async def execute_transfer(self, user, from_wallet_id, to_wallet_id):
        """
        Run sync business logic inside async test.
        """
        await sync_to_async(
            transfer
        )(
            from_wallet_id=from_wallet_id,
            to_wallet_id=to_wallet_id,
            amount=Decimal("500"),
            idempotency_key="ws-test-transfer-001",
            user=user,
            description="websocket notification test",
        )

    @staticmethod
    async def get_access_token(self, user):
        token = await sync_to_async(RefreshToken.for_user)(user)
        return str(token.access_token)

    @staticmethod
    async def create_user(username, email, mobile):
        return await sync_to_async(
            User.objects.create_user
        )(
            username=username,
            password="password123",
            mobile=mobile,
            email=email,
        )

    @staticmethod
    async def create_currency(code):
        return await sync_to_async(
            Currency.objects.create
        )(
            code=code,
            name="USD",
        )

    @staticmethod
    async def create_wallet(user, currency, balance):
        return await sync_to_async(
            Wallet.objects.create
        )(
            user=user,
            currency=currency,
            balance=balance
        )
