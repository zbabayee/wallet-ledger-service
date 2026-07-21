from decimal import Decimal
from unittest.mock import patch, MagicMock
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from apps.transactions.models import (
    LedgerDirection,
    Transaction,
    TransactionLedger,
    TransactionStatus,
    TransactionType,
)
from apps.transactions.services.transaction_service import deposit, withdraw, transfer
from apps.wallets.models import Wallet, WalletStatus, Currency

User = get_user_model()


class DepositServiceTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="zahra",
            email="zahra@test.com",
            mobile="09130650477",
            password="12345678",
        )

        self.currency = Currency.objects.create(
            code="USD",
            name="US Dollar",
        )

        self.wallet = Wallet.objects.create(
            user=self.user,
            currency=self.currency,
            balance=Decimal("100.00"),
            status=WalletStatus.ACTIVE,
        )

    def test_deposit_success(self):
        txn, replayed = deposit(
            wallet_id=self.wallet.id,
            amount=Decimal("50.00"),
            idempotency_key=str(uuid4()),
            user=self.user,
            description="Salary",
        )

        self.wallet.refresh_from_db()
        self.assertFalse(replayed)
        self.assertEqual(self.wallet.balance,Decimal("150.00"),)
        self.assertEqual(txn.status, TransactionStatus.COMPLETED)
        self.assertEqual(txn.transaction_type,TransactionType.DEPOSIT)
        self.assertEqual(TransactionLedger.objects.count(), 1)

        ledger = TransactionLedger.objects.first()
        self.assertEqual(ledger.direction, LedgerDirection.CREDIT,)
        self.assertEqual(ledger.balance_after, Decimal("150.00"),)

    def test_deposit_to_inactive_wallet(self):
        self.wallet.status = WalletStatus.FROZEN
        self.wallet.save()

        txn, replayed = deposit(
            wallet_id=self.wallet.id,
            amount=Decimal("50"),
            idempotency_key=str(uuid4()),
            user=self.user,
        )

        self.wallet.refresh_from_db()
        self.assertFalse(replayed)
        self.assertEqual(txn.status,TransactionStatus.FAILED)
        self.assertEqual(txn.failure_reason,"Wallet is not active.")
        self.assertEqual(self.wallet.balance, Decimal("100.00"))
        self.assertEqual(TransactionLedger.objects.count(), 0)

    def test_deposit_is_idempotent(self):
        key = str(uuid4())

        txn1, replayed1 = deposit(
            wallet_id=self.wallet.id,
            amount=Decimal("25"),
            idempotency_key=key,
            user=self.user,
        )

        txn2, replayed2 = deposit(
            wallet_id=self.wallet.id,
            amount=Decimal("25"),
            idempotency_key=key,
            user=self.user,
        )

        self.wallet.refresh_from_db()
        self.assertFalse(replayed1)
        self.assertTrue(replayed2)
        self.assertEqual(txn1.id,txn2.id)
        self.assertEqual(self.wallet.balance,Decimal("125.00"))
        self.assertEqual(Transaction.objects.count(),1)
        self.assertEqual( TransactionLedger.objects.count(),1)


class WithdrawServiceTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="zahra",
            email="zahra@test.com",
            password="12345678",
            mobile="09130650444"
        )

        self.currency = Currency.objects.create(
            code="USD",
            name="US Dollar",
        )

        self.wallet = Wallet.objects.create(
            user=self.user,
            currency=self.currency,
            balance=Decimal("100.00"),
            status=WalletStatus.ACTIVE,
        )

    def test_withdraw_success(self):
        txn, replayed = withdraw(
            wallet_id=self.wallet.id,
            amount=Decimal("40.00"),
            idempotency_key=str(uuid4()),
            user=self.user,
            description="ATM Withdrawal",
        )

        self.wallet.refresh_from_db()
        self.assertFalse(replayed)
        self.assertEqual(self.wallet.balance,Decimal("60.00"))
        self.assertEqual(txn.status,TransactionStatus.COMPLETED)
        self.assertEqual(txn.transaction_type, TransactionType.WITHDRAW)
        self.assertEqual(TransactionLedger.objects.count(),1)
        ledger = TransactionLedger.objects.first()
        self.assertEqual(ledger.direction, LedgerDirection.DEBIT)
        self.assertEqual(ledger.balance_after, Decimal("60.00"))

    def test_withdraw_insufficient_balance(self):
        txn, replayed = withdraw(
            wallet_id=self.wallet.id,
            amount=Decimal("150.00"),
            idempotency_key=str(uuid4()),
            user=self.user,
        )
        self.wallet.refresh_from_db()
        self.assertFalse(replayed)
        self.assertEqual(txn.status, TransactionStatus.FAILED)
        self.assertEqual(txn.failure_reason, "Insufficient balance.")
        self.assertEqual(self.wallet.balance, Decimal("100.00"))
        self.assertEqual(TransactionLedger.objects.count(), 0)

    def test_withdraw_inactive_wallet(self):
        self.wallet.status = WalletStatus.FROZEN
        self.wallet.save()

        txn, replayed = withdraw(
            wallet_id=self.wallet.id,
            amount=Decimal("10.00"),
            idempotency_key=str(uuid4()),
            user=self.user,
        )

        self.wallet.refresh_from_db()
        self.assertFalse(replayed)
        self.assertEqual(txn.status,TransactionStatus.FAILED)
        self.assertEqual(txn.failure_reason,"Wallet is not active.")
        self.assertEqual(self.wallet.balance,Decimal("100.00"))
        self.assertEqual(TransactionLedger.objects.count(),0)

    def test_withdraw_is_idempotent(self):
        key = str(uuid4())

        txn1, replayed1 = withdraw(
            wallet_id=self.wallet.id,
            amount=Decimal("25.00"),
            idempotency_key=key,
            user=self.user,
        )

        txn2, replayed2 = withdraw(
            wallet_id=self.wallet.id,
            amount=Decimal("25.00"),
            idempotency_key=key,
            user=self.user,
        )

        self.wallet.refresh_from_db()
        self.assertFalse(replayed1)
        self.assertTrue(replayed2)
        self.assertEqual(txn1.id,txn2.id,)
        self.assertEqual(self.wallet.balance, Decimal("75.00"))
        self.assertEqual(Transaction.objects.count(),1,)
        self.assertEqual(TransactionLedger.objects.count(),1)


class TransferServiceTests(TestCase):

    def setUp(self):
        self.user1 = User.objects.create_user(
            username="user1",
            email="user1@test.com",
            password="12345678",
            mobile="09130650445"
        )

        self.user2 = User.objects.create_user(
            username="user2",
            email="user2@test.com",
            password="12345678",
            mobile="09130650448"
        )

        self.currency = Currency.objects.create(
            code="USD",
            name="US Dollar",
        )

        self.wallet1 = Wallet.objects.create(
            user=self.user1,
            currency=self.currency,
            balance=Decimal("1000.00"),
            status=WalletStatus.ACTIVE,
        )

        self.wallet2 = Wallet.objects.create(
            user=self.user2,
            currency=self.currency,
            balance=Decimal("500.00"),
            status=WalletStatus.ACTIVE,
        )

    def test_transfer_success(self):
        txn, replayed = transfer(
            from_wallet_id=self.wallet1.id,
            to_wallet_id=self.wallet2.id,
            amount=Decimal("200.00"),
            idempotency_key=str(uuid4()),
            user=self.user1,
        )

        self.wallet1.refresh_from_db()
        self.wallet2.refresh_from_db()

        self.assertFalse(replayed)

        self.assertEqual(
            txn.status,
            TransactionStatus.COMPLETED,
        )

        self.assertEqual(
            self.wallet1.balance,
            Decimal("800.00"),
        )

        self.assertEqual(
            self.wallet2.balance,
            Decimal("700.00"),
        )

        self.assertEqual(
            TransactionLedger.objects.count(),
            2,
        )

    def test_transfer_insufficient_balance(self):
        txn, replayed = transfer(
            from_wallet_id=self.wallet1.id,
            to_wallet_id=self.wallet2.id,
            amount=Decimal("5000.00"),
            idempotency_key=str(uuid4()),
            user=self.user1,
        )

        self.wallet1.refresh_from_db()
        self.wallet2.refresh_from_db()
        self.assertFalse(replayed)
        self.assertEqual(txn.status, TransactionStatus.FAILED)
        self.assertEqual(txn.failure_reason,"Insufficient balance.")
        self.assertEqual(self.wallet1.balance,Decimal("1000.00"))
        self.assertEqual(self.wallet2.balance, Decimal("500.00"))
        self.assertEqual(TransactionLedger.objects.count(),0)

    def test_transfer_inactive_wallet(self):
        self.wallet2.status = WalletStatus.FROZEN
        self.wallet2.save()

        txn, replayed = transfer(
            from_wallet_id=self.wallet1.id,
            to_wallet_id=self.wallet2.id,
            amount=Decimal("10"),
            idempotency_key=str(uuid4()),
            user=self.user1,
        )

        self.assertFalse(replayed)
        self.assertEqual(txn.status, TransactionStatus.FAILED)
        self.assertEqual(txn.failure_reason,"One of the wallets is not active.")

    def test_transfer_same_wallet(self):
        with self.assertRaises(ValueError):
            transfer(
                from_wallet_id=self.wallet1.id,
                to_wallet_id=self.wallet1.id,
                amount=Decimal("10"),
                idempotency_key=str(uuid4()),
                user=self.user1,
            )

    def test_transfer_idempotent(self):
        key = str(uuid4())

        txn1, replayed1 = transfer(
            from_wallet_id=self.wallet1.id,
            to_wallet_id=self.wallet2.id,
            amount=Decimal("50"),
            idempotency_key=key,
            user=self.user1,
        )

        txn2, replayed2 = transfer(
            from_wallet_id=self.wallet1.id,
            to_wallet_id=self.wallet2.id,
            amount=Decimal("50"),
            idempotency_key=key,
            user=self.user1,
        )

        self.wallet1.refresh_from_db()
        self.wallet2.refresh_from_db()
        self.assertFalse(replayed1)
        self.assertTrue(replayed2)
        self.assertEqual(txn1.id, txn2.id)
        self.assertEqual(self.wallet1.balance,Decimal("950.00"))
        self.assertEqual(self.wallet2.balance, Decimal("550.00"))
        self.assertEqual(Transaction.objects.count(),1)
        self.assertEqual(TransactionLedger.objects.count(),2)

    @patch("apps.transactions.services.transaction_service.async_to_sync")
    @patch("apps.transactions.services.transaction_service.get_channel_layer")
    @patch("apps.transactions.tasks.notify_monitoring_team.delay")
    def test_large_transfer_triggers_celery_and_websocket(
        self,
        mock_notify,
        mock_get_channel_layer,
        mock_async_to_sync,
    ):
        """
        Large transfers should:
        - enqueue Celery task
        - send websocket notification
        """
        channel_layer = MagicMock()
        mock_get_channel_layer.return_value = channel_layer
        websocket_sender = MagicMock()
        mock_async_to_sync.return_value = websocket_sender
        txn, replayed = transfer(
            from_wallet_id=self.wallet1.id,
            to_wallet_id=self.wallet2.id,
            amount=Decimal("15000.00"),
            idempotency_key=str(uuid4()),
            user=self.user1,
        )

        self.assertFalse(replayed)
        mock_notify.assert_called_once_with(txn.id)
        mock_async_to_sync.assert_called_once_with(
            channel_layer.group_send
        )
        websocket_sender.assert_called_once()
        group_name, payload = websocket_sender.call_args[0]

        self.assertEqual(group_name,f"user_{self.wallet2.user_id}")
        self.assertEqual(payload["type"],"wallet_notification")
        self.assertEqual(payload["data"]["transaction_id"],str(txn.transaction_uuid))
        self.assertEqual(payload["data"]["amount"],"15000.00")

    @patch("apps.transactions.services.transaction_service.async_to_sync")
    @patch("apps.transactions.services.transaction_service.get_channel_layer")
    @patch("apps.transactions.tasks.notify_monitoring_team.delay")
    def test_small_transfer_only_sends_websocket(
        self,
        mock_notify,
        mock_get_channel_layer,
        mock_async_to_sync,
    ):
        """
        Small transfers should not enqueue Celery
        but MUST send websocket notification.
        """

        channel_layer = MagicMock()
        mock_get_channel_layer.return_value = channel_layer
        websocket_sender = MagicMock()
        mock_async_to_sync.return_value = websocket_sender

        transfer(
            from_wallet_id=self.wallet1.id,
            to_wallet_id=self.wallet2.id,
            amount=Decimal("100.00"),
            idempotency_key=str(uuid4()),
            user=self.user1,
        )
        mock_notify.assert_not_called()
        mock_async_to_sync.assert_called_once_with(
            channel_layer.group_send
        )
        websocket_sender.assert_called_once()

    @patch("apps.transactions.services.transaction_service.async_to_sync")
    @patch("apps.transactions.services.transaction_service.get_channel_layer")
    def test_websocket_payload(
        self,
        mock_get_channel_layer,
        mock_async_to_sync,
    ):
        """
        Verify websocket payload fields.
        """

        channel_layer = MagicMock()
        mock_get_channel_layer.return_value = channel_layer
        websocket_sender = MagicMock()
        mock_async_to_sync.return_value = websocket_sender
        txn, _ = transfer(
            from_wallet_id=self.wallet1.id,
            to_wallet_id=self.wallet2.id,
            amount=Decimal("250.00"),
            idempotency_key=str(uuid4()),
            user=self.user1,
        )

        _, payload = websocket_sender.call_args[0]
        self.assertEqual(payload["type"],"wallet_notification")
        data = payload["data"]
        self.assertEqual(data["transaction_id"], str(txn.transaction_uuid))
        self.assertEqual(data["amount"], "250.00")
        self.assertEqual(data["currency"],"USD")
        self.assertEqual(data["sender_wallet"], str(self.wallet1.wallet_uuid))
        self.assertEqual(data["recipient_wallet"],str(self.wallet2.wallet_uuid))
        self.assertIn("250.00",data["message"])

    @patch("apps.transactions.tasks.notify_monitoring_team.delay")
    @patch("apps.transactions.services.transaction_service.async_to_sync")
    def test_failed_transfer_sends_no_notification(
        self,
        mock_async_to_sync,
        mock_notify,
    ):
        """
        Failed transfers must not trigger
        websocket or celery.
        """
        transfer(
            from_wallet_id=self.wallet1.id,
            to_wallet_id=self.wallet2.id,
            amount=Decimal("500000.00"),
            idempotency_key=str(uuid4()),
            user=self.user1,
        )
        mock_notify.assert_not_called()
        mock_async_to_sync.assert_not_called()

class TransferAPIViewTests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="zahra",
            password="12345678",
            email="zahra@test.com",
            mobile="09130650485"
        )

        self.receiver = User.objects.create_user(
            username="receiver",
            password="12345678",
            email="receiver@test.com",
            mobile="09130650489"
        )

        self.client.force_authenticate(self.user)

        self.currency = Currency.objects.create(
            code="USD",
            name="US Dollar",
        )

        self.source_wallet = Wallet.objects.create(
            user=self.user,
            currency=self.currency,
            balance=Decimal("1000"),
        )

        self.destination_wallet = Wallet.objects.create(
            user=self.receiver,
            currency=self.currency,
            balance=Decimal("200"),
        )

        self.url = reverse("transfer")


    @patch("apps.transactions.api.views.transfer")
    def test_successful_transfer(self, mock_transfer):

        txn = Transaction.objects.create(
            transaction_type=TransactionType.TRANSFER,
            from_wallet=self.source_wallet,
            to_wallet=self.destination_wallet,
            amount=Decimal("100"),
            status=TransactionStatus.COMPLETED,
            idempotency_key=str(uuid4()),
            created_by=self.user,
            reference_number=str(uuid4())
        )

        mock_transfer.return_value = (txn, False)

        idempotency_key = str(uuid4())

        response = self.client.post(
            self.url,
            {
                "from_wallet": self.source_wallet.id,
                "to_wallet": self.destination_wallet.id,
                "amount": "100",
                "idempotency_key": idempotency_key,
                "description": "test transfer",
            },
            format="json",
        )


        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )


        mock_transfer.assert_called_once_with(
            from_wallet_id=self.source_wallet.id,
            to_wallet_id=self.destination_wallet.id,
            amount=Decimal("100"),
            idempotency_key=idempotency_key,
            user=self.user,
            description="test transfer",
        )


    @patch("apps.transactions.api.views.transfer")
    def test_idempotent_transfer_returns_200(
        self,
        mock_transfer,
    ):

        txn = Transaction.objects.create(
            transaction_type=TransactionType.TRANSFER,
            from_wallet=self.source_wallet,
            to_wallet=self.destination_wallet,
            amount=Decimal("100"),
            status=TransactionStatus.COMPLETED,
            idempotency_key=str(uuid4()),
            created_by=self.user,
            reference_number=str(uuid4())
        )

        mock_transfer.return_value = (
            txn,
            True,
        )


        response = self.client.post(
            self.url,
            {
                "from_wallet": self.source_wallet.id,
                "to_wallet": self.destination_wallet.id,
                "amount": "100",
                "idempotency_key": str(uuid4()),
            },
            format="json",
        )


        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )


    def test_same_wallet_transfer_validation(self):

        response = self.client.post(
            self.url,
            {
                "from_wallet": self.source_wallet.id,
                "to_wallet": self.source_wallet.id,
                "amount": "100",
                "idempotency_key": str(uuid4()),
            },
            format="json",
        )


        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )


    def test_invalid_amount(self):

        response = self.client.post(
            self.url,
            {
                "from_wallet": self.source_wallet.id,
                "to_wallet": self.destination_wallet.id,
                "amount": "-50",
                "idempotency_key": str(uuid4()),
            },
            format="json",
        )


        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )


    def test_requires_authentication(self):

        self.client.force_authenticate(
            user=None
        )


        response = self.client.post(
            self.url,
            {
                "from_wallet": self.source_wallet.id,
                "to_wallet": self.destination_wallet.id,
                "amount": "100",
                "idempotency_key": str(uuid4()),
            },
            format="json",
        )


        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )


    def test_currency_mismatch_validation(self):

        eur_currency = Currency.objects.create(
            code="EUR",
            name="Euro",
        )

        another_wallet = Wallet.objects.create(
            user=self.receiver,
            currency=eur_currency,
            balance=Decimal("500"),
        )


        response = self.client.post(
            self.url,
            {
                "from_wallet": self.source_wallet.id,
                "to_wallet": another_wallet.id,
                "amount": "100",
                "idempotency_key": str(uuid4()),
            },
            format="json",
        )


        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )