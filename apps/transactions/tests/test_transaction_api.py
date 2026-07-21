from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.transactions.models import Transaction, TransactionStatus, TransactionType
from apps.wallets.models import Currency, Wallet


class DepositAPIViewTests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="zahra",
            password="12345678",
        )

        self.client.force_authenticate(self.user)

        self.currency = Currency.objects.create(
            code="USD",
            name="US Dollar",
        )

        self.wallet = Wallet.objects.create(
            user=self.user,
            currency=self.currency,
            balance=Decimal("100"),
        )

        self.url = reverse("deposit")

    @patch("transactions.api.views.deposit")
    def test_successful_deposit(self, mock_deposit):
        txn = Transaction.objects.create(
            transaction_type=TransactionType.DEPOSIT,
            to_wallet=self.wallet,
            amount=Decimal("50"),
            status=TransactionStatus.COMPLETED,
            idempotency_key=str(uuid4()),
            created_by=self.user,
        )

        mock_deposit.return_value = (txn, False)

        response = self.client.post(
            self.url,
            {
                "wallet": self.wallet.id,
                "amount": "50",
                "idempotency_key": str(uuid4()),
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        mock_deposit.assert_called_once()

    @patch("transactions.api.views.deposit")
    def test_successful_deposit(self, mock_deposit):
        txn = Transaction.objects.create(
            transaction_type=TransactionType.DEPOSIT,
            to_wallet=self.wallet,
            amount=Decimal("50"),
            status=TransactionStatus.COMPLETED,
            idempotency_key=str(uuid4()),
            created_by=self.user,
        )

        mock_deposit.return_value = (txn, False)

        response = self.client.post(
            self.url,
            {
                "wallet": self.wallet.id,
                "amount": "50",
                "idempotency_key": str(uuid4()),
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        mock_deposit.assert_called_once()

    @patch("transactions.api.views.deposit")
    def test_idempotent_request_returns_200(self, mock_deposit):
        txn = Transaction.objects.create(
            transaction_type=TransactionType.DEPOSIT,
            to_wallet=self.wallet,
            amount=Decimal("50"),
            status=TransactionStatus.COMPLETED,
            idempotency_key=str(uuid4()),
            created_by=self.user,
        )

        mock_deposit.return_value = (txn, True)

        response = self.client.post(
            self.url,
            {
                "wallet": self.wallet.id,
                "amount": "50",
                "idempotency_key": str(uuid4()),
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_invalid_amount(self):
        response = self.client.post(
            self.url,
            {
                "wallet": self.wallet.id,
                "amount": "-10",
                "idempotency_key": str(uuid4()),
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_requires_authentication(self):
        self.client.logout()

        response = self.client.post(
            self.url,
            {
                "wallet": self.wallet.id,
                "amount": "20",
                "idempotency_key": str(uuid4()),
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class WithdrawAPIViewTests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="zahra",
            password="12345678",
        )

        self.client.force_authenticate(self.user)

        self.currency = Currency.objects.create(
            code="USD",
            name="US Dollar",
        )

        self.wallet = Wallet.objects.create(
            user=self.user,
            currency=self.currency,
            balance=Decimal("500"),
        )

        self.url = reverse("withdraw")

    @patch("transactions.api.views.withdraw")
    def test_successful_withdraw(self, mock_withdraw):
        txn = Transaction.objects.create(
            transaction_type=TransactionType.WITHDRAW,
            from_wallet=self.wallet,
            amount=Decimal("100"),
            status=TransactionStatus.COMPLETED,
            idempotency_key=str(uuid4()),
            created_by=self.user,
        )

        mock_withdraw.return_value = (txn, False)

        response = self.client.post(
            self.url,
            {
                "wallet": self.wallet.id,
                "amount": "100",
                "idempotency_key": str(uuid4()),
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        mock_withdraw.assert_called_once_with(
            wallet_id=self.wallet.id,
            amount=Decimal("100"),
            idempotency_key=mock_withdraw.call_args.kwargs["idempotency_key"],
            user=self.user,
            description="",
        )

    @patch("transactions.api.views.withdraw")
    def test_idempotent_request_returns_200(self, mock_withdraw):
        txn = Transaction.objects.create(
            transaction_type=TransactionType.WITHDRAW,
            from_wallet=self.wallet,
            amount=Decimal("100"),
            status=TransactionStatus.COMPLETED,
            idempotency_key=str(uuid4()),
            created_by=self.user,
        )

        mock_withdraw.return_value = (txn, True)

        response = self.client.post(
            self.url,
            {
                "wallet": self.wallet.id,
                "amount": "100",
                "idempotency_key": str(uuid4()),
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_invalid_amount(self):
        response = self.client.post(
            self.url,
            {
                "wallet": self.wallet.id,
                "amount": "-10",
                "idempotency_key": str(uuid4()),
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_requires_authentication(self):
        self.client.force_authenticate(user=None)

        response = self.client.post(
            self.url,
            {
                "wallet": self.wallet.id,
                "amount": "100",
                "idempotency_key": str(uuid4()),
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TransactionListAPIViewTests(APITestCase):

    def setUp(self):
        self.user1 = User.objects.create_user(
            username="user1",
            password="password123",
        )

        self.user2 = User.objects.create_user(
            username="user2",
            password="password123",
        )
        self.currency = Currency.objects.create(code="USD", name="US Dollar")

        self.wallet1 = Wallet.objects.create(
            user=self.user1,
            balance=Decimal("1000"),
            currency=self.currency,
        )

        self.wallet2 = Wallet.objects.create(
            user=self.user2,
            balance=Decimal("500"),
            currency=self.currency,
        )

        self.url = reverse("transaction-list")

    def authenticate(self, user):
        self.client.force_authenticate(user=user)

    def create_transaction(
            self,
            *,
            from_wallet=None,
            to_wallet=None,
            user,
            amount="100",
    ):
        return Transaction.objects.create(
            transaction_type=TransactionType.TRANSFER,
            from_wallet=from_wallet,
            to_wallet=to_wallet,
            amount=Decimal(amount),
            status=TransactionStatus.COMPLETED,
            created_by=user,
        )

    def test_authenticated_user_can_get_transactions(self):
        self.authenticate(self.user1)
        transaction = self.create_transaction(
            from_wallet=self.wallet1,
            to_wallet=self.wallet2,
            user=self.user1,
        )
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"] if "results" in response.data else response.data
        transaction_ids = [
            item["id"]
            for item in results
        ]
        self.assertIn(transaction.id, transaction_ids)

    def test_user_can_only_see_own_transactions(self):
        self.authenticate(self.user1)
        own_transaction = self.create_transaction(
            from_wallet=self.wallet1,
            to_wallet=self.wallet2,
            user=self.user1,
        )
        other_transaction = self.create_transaction(
            from_wallet=self.wallet2,
            to_wallet=self.wallet1,
            user=self.user2,
        )

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"] if "results" in response.data else response.data
        transaction_ids = [
            item["id"]
            for item in results
        ]
        self.assertIn(own_transaction.id, transaction_ids)
        self.assertNotIn(other_transaction.id, transaction_ids)

    def test_transaction_list_requires_authentication(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_empty_transaction_list(self):
        self.authenticate(self.user1)
        response = self.client.get(self.url)
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        results = response.data["results"] if "results" in response.data else response.data
        self.assertEqual(len(results), 0)

    def test_transactions_are_ordered_by_created_at_desc(self):
        self.authenticate(self.user1)
        first = self.create_transaction(
            from_wallet=self.wallet1,
            to_wallet=self.wallet2,
            user=self.user1,
            amount="100",
        )

        second = self.create_transaction(
            from_wallet=self.wallet1,
            to_wallet=self.wallet2,
            user=self.user1,
            amount="200",
        )

        response = self.client.get(self.url)
        results = response.data["results"] if "results" in response.data else response.data

        ids = [
            item["id"]
            for item in results
        ]

        self.assertEqual(ids[0], second.id)
        self.assertEqual(ids[1], first.id)
