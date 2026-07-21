from concurrent.futures import ThreadPoolExecutor, as_completed
from decimal import Decimal

from django.test import TransactionTestCase

from apps.accounts.models import User
from apps.transactions.models import (
    Transaction,
    TransactionStatus,
)
from apps.transactions.services.transaction_service import transfer
from apps.transactions.services.transaction_service import withdraw
from apps.wallets.models import Wallet


class TransactionConcurrencyTests(TransactionTestCase):
    """
    Tests database locking and race-condition handling.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            password="password123",
        )

        self.wallet = Wallet.objects.create(
            user=self.user,
            balance=Decimal("100"),
            status="ACTIVE",
        )

    def execute_withdraw(self):
        return withdraw(
            wallet_id=self.wallet.id,
            amount=Decimal("80"),
            idempotency_key=str(self.wallet.id) + "-key-" + str(id(self)),
            user=self.user,
        )

    def test_concurrent_withdraw_should_not_double_spend(self):
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(
                executor.map(
                    lambda _: self.execute_withdraw(),
                    range(2),
                )
            )

        successful = [
            txn
            for txn, replayed in results
            if txn.status == TransactionStatus.COMPLETED
        ]

        failed = [
            txn
            for txn, replayed in results
            if txn.status == TransactionStatus.FAILED
        ]

        self.assertEqual(len(successful), 1, "Only one withdrawal should succeed")
        self.assertEqual(len(failed), 1, "Second withdrawal should fail")
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("20"))


class TransferConcurrencyTests(TransactionTestCase):
    """
    Tests database locking and race-condition protection
    in concurrent transfers.
    """
    reset_sequences = True
    def setUp(self):
        self.user1 = User.objects.create_user(
            username="user1",
            password="test123",
        )

        self.user2 = User.objects.create_user(
            username="user2",
            password="test123",
        )
        self.wallet_a = Wallet.objects.create(
            user=self.user1,
            balance=Decimal("1000"),
            currency_id=1,
        )
        self.wallet_b = Wallet.objects.create(
            user=self.user2,
            balance=Decimal("0"),
            currency_id=1,
        )

    def _make_transfer(self, key):
        return transfer(
            from_wallet_id=self.wallet_a.id,
            to_wallet_id=self.wallet_b.id,
            amount=Decimal("800"),
            idempotency_key=key,
            user=self.user1,
        )

    def test_concurrent_transfer_should_not_double_spend(self):
        """
        Two concurrent transfers from same wallet
        should not both succeed.
        """
        keys = [
            "transfer-1",
            "transfer-2",
        ]

        results = []

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(
                    self._make_transfer,
                    key,
                )
                for key in keys
            ]

            for future in as_completed(futures):
                results.append(future.result())

        self.wallet_a.refresh_from_db()
        self.wallet_b.refresh_from_db()

        successful = [
            txn
            for txn, replayed in results
            if txn.status == TransactionStatus.COMPLETED
        ]

        failed = [
            txn
            for txn, replayed in results
            if txn.status == TransactionStatus.FAILED
        ]
        # only one transfer can pass
        self.assertEqual(len(successful), 1)
        self.assertEqual(len(failed), 1)

        # balance must never become negative
        self.assertEqual(self.wallet_a.balance, Decimal("200"))
        self.assertEqual(self.wallet_b.balance, Decimal("800"))

    def test_concurrent_opposite_transfers_should_not_deadlock(self):
        """
        Tests A -> B and B -> A at the same time.
        Because wallets are locked in sorted order,
        deadlock should not happen.
        """

        def transfer_a_to_b():
            return transfer(
                from_wallet_id=self.wallet_a.id,
                to_wallet_id=self.wallet_b.id,
                amount=Decimal("100"),
                idempotency_key="a-to-b",
                user=self.user1,
            )

        def transfer_b_to_a():
            return transfer(
                from_wallet_id=self.wallet_b.id,
                to_wallet_id=self.wallet_a.id,
                amount=Decimal("50"),
                idempotency_key="b-to-a",
                user=self.user2,
            )

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(transfer_a_to_b),
                executor.submit(transfer_b_to_a),
            ]
            results = [
                future.result(timeout=10)
                for future in futures
            ]

        self.wallet_a.refresh_from_db()
        self.wallet_b.refresh_from_db()
        completed = [
            txn
            for txn, replayed in results
            if txn.status == TransactionStatus.COMPLETED
        ]

        self.assertEqual(len(completed), 2)
        self.assertEqual(self.wallet_a.balance, Decimal("950"))
        self.assertEqual(self.wallet_b.balance, Decimal("50"))
        self.assertEqual(Transaction.objects.count(), 2)
