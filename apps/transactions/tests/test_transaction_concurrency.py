from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from uuid import uuid4

from django.test import TransactionTestCase

from apps.accounts.models import User
from apps.transactions.models import Transaction, TransactionStatus
from apps.transactions.services.transaction_service import withdraw, transfer
from apps.wallets.models import Wallet, Currency


class TransactionConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            password="password123",
            email="testuser@gmail.com",
            mobile="09131111117",
        )
        self.currency = Currency.objects.create(code="USD", name="US Dollar")
        self.wallet = Wallet.objects.create(
            user=self.user,
            balance=Decimal("100"),
            status="ACTIVE",
            currency=self.currency,
        )

    def test_concurrent_withdraw_should_not_double_spend(self):
        def execute_withdraw():
            return withdraw(
                wallet_id=self.wallet.id,
                amount=Decimal("80"),
                idempotency_key=str(uuid4()),
                user=self.user,
            )

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _: execute_withdraw(), range(2)))

        successful = [txn for txn, _ in results if txn.status == TransactionStatus.COMPLETED]
        failed = [txn for txn, _ in results if txn.status == TransactionStatus.FAILED]

        self.assertEqual(len(successful), 1, "فقط یک برداشت باید موفق باشد")
        self.assertEqual(len(failed), 1, "برداشت دوم باید شکست بخورد")
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("20"))


class TransferConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(
            username="user1", password="test123", email="user1@gmail.com", mobile="09131111116"
        )
        self.user2 = User.objects.create_user(
            username="user2", password="test123", email="user2@gmail.com", mobile="09131111115"
        )
        self.currency = Currency.objects.create(code="USD", name="US Dollar")
        self.wallet_a = Wallet.objects.create(
            user=self.user1, balance=Decimal("1000"), currency=self.currency
        )
        self.wallet_b = Wallet.objects.create(
            user=self.user2,
            balance=Decimal("100"),
            currency=self.currency
        )

    def test_concurrent_transfer_should_not_double_spend(self):
        keys = [str(uuid4()), str(uuid4())]
        results = []

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(
                    transfer,
                    from_wallet_id=self.wallet_a.id,
                    to_wallet_id=self.wallet_b.id,
                    amount=Decimal("800"),
                    idempotency_key=key,
                    user=self.user1,
                )
                for key in keys
            ]
            for future in futures:
                results.append(future.result())

        self.wallet_a.refresh_from_db()
        self.wallet_b.refresh_from_db()

        successful = [txn for txn, _ in results if txn.status == TransactionStatus.COMPLETED]
        failed = [txn for txn, _ in results if txn.status == TransactionStatus.FAILED]

        self.assertEqual(len(successful), 1)
        self.assertEqual(len(failed), 1)
        self.assertEqual(self.wallet_a.balance, Decimal("200"))
        self.assertEqual(self.wallet_b.balance, Decimal("900"))

    def test_concurrent_opposite_transfers_should_not_deadlock(self):
        def transfer_a_to_b():
            return transfer(
                from_wallet_id=self.wallet_a.id,
                to_wallet_id=self.wallet_b.id,
                amount=Decimal("100"),
                idempotency_key=str(uuid4()),
                user=self.user1,
            )

        def transfer_b_to_a():
            return transfer(
                from_wallet_id=self.wallet_b.id,
                to_wallet_id=self.wallet_a.id,
                amount=Decimal("50"),
                idempotency_key=str(uuid4()),
                user=self.user2,
            )

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(transfer_a_to_b),
                executor.submit(transfer_b_to_a),
            ]
            results = [f.result(timeout=10) for f in futures]

        self.wallet_a.refresh_from_db()
        self.wallet_b.refresh_from_db()

        completed = [txn for txn, _ in results if txn.status == TransactionStatus.COMPLETED]
        self.assertEqual(len(completed), 2)

        self.assertEqual(self.wallet_a.balance, Decimal("950"))
        self.assertEqual(self.wallet_b.balance, Decimal("150"))
        self.assertEqual(Transaction.objects.count(), 2)