from decimal import Decimal
from uuid import UUID, uuid4

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction as db_transaction
from django.utils import timezone

from apps.transactions.models import (
    LedgerDirection,
    Transaction,
    TransactionLedger,
    TransactionStatus,
    TransactionType,
)
from apps.wallets.models import Wallet, WalletStatus

LARGE_TRANSFER_THRESHOLD = Decimal("10000")

def _generate_reference_number():
    return f"TXN-{uuid4().hex[:12].upper()}"

def _get_or_create_pending_transaction(
        *,
        idempotency_key: str,
        defaults: dict,
):
    """
    Returns:
        (transaction, created)
    """
    return Transaction.objects.get_or_create(
        idempotency_key=idempotency_key,
        defaults=defaults,
    )


def _complete(txn: Transaction) -> None:
    txn.status = TransactionStatus.COMPLETED
    txn.completed_at = timezone.now()
    txn.save(
        update_fields=[
            "status",
            "completed_at",
            "updated_at",
        ]
    )


def _fail(txn: Transaction, reason: str) -> None:
    txn.status = TransactionStatus.FAILED
    txn.failure_reason = reason
    txn.save(
        update_fields=[
            "status",
            "failure_reason",
            "updated_at",
        ]
    )


def deposit(
        *,
        wallet_id: int,
        amount: Decimal,
        idempotency_key: str,
        user,
        description: str = "",
):

    txn, created = _get_or_create_pending_transaction(
        idempotency_key=idempotency_key,
        defaults={
            "transaction_type": TransactionType.DEPOSIT,
            "to_wallet_id": wallet_id,
            "amount": amount,
            "description": description,
            "created_by": user,
            "reference_number": _generate_reference_number()
        },
    )

    if not created:
        return txn, True

    with db_transaction.atomic():
        wallet = Wallet.objects.select_for_update().filter(pk=wallet_id).first()

        if wallet is None:
            _fail(txn, "Wallet not found.")
            return txn, False

        if wallet.status != WalletStatus.ACTIVE:
            _fail(txn, "Wallet is not active.")
            return txn, False

        wallet.balance += amount
        wallet.save(update_fields=["balance", "updated_at"])

        _complete(txn)
        TransactionLedger.objects.create(transaction=txn,
                                         wallet=wallet,
                                         direction=LedgerDirection.CREDIT,
                                         amount=amount,
                                         balance_after=wallet.balance,
                                         )

    return txn, False


def withdraw(
        *,
        wallet_id: int,
        amount: Decimal,
        idempotency_key: str,
        user,
        description: str = "",
):
    txn, created = _get_or_create_pending_transaction(
        idempotency_key=idempotency_key,
        defaults={
            "transaction_type": TransactionType.WITHDRAW,
            "from_wallet_id": wallet_id,
            "amount": amount,
            "description": description,
            "created_by": user,
            "reference_number": _generate_reference_number()
        },
    )

    if not created:
        return txn, True

    with db_transaction.atomic():

        wallet = Wallet.objects.select_for_update().filter(pk=wallet_id).first()

        if wallet is None:
            _fail(txn, "Wallet not found.")
            return txn, False

        if wallet.status != WalletStatus.ACTIVE:
            _fail(txn, "Wallet is not active.")
            return txn, False

        if wallet.balance < amount:
            _fail(txn, "Insufficient balance.")
            return txn, False

        wallet.balance -= amount
        wallet.save(update_fields=["balance", "updated_at"])
        _complete(txn)

        TransactionLedger.objects.create(
            transaction=txn,
            wallet=wallet,
            direction=LedgerDirection.DEBIT,
            amount=amount,
            balance_after=wallet.balance,
        )


    return txn, False


def transfer(
    *,
    from_wallet_id: UUID,
    to_wallet_id: UUID,
    amount: Decimal,
    idempotency_key: str,
    user,
    description: str = "",
):
    if from_wallet_id == to_wallet_id:
        raise ValueError(
            "from_wallet_id and to_wallet_id must differ."
        )

    txn, created = _get_or_create_pending_transaction(
        idempotency_key=idempotency_key,
        defaults={
            "transaction_type": TransactionType.TRANSFER,
            "from_wallet_id": from_wallet_id,
            "to_wallet_id": to_wallet_id,
            "amount": amount,
            "description": description,
            "created_by": user,
            "reference_number": _generate_reference_number()
        },
    )

    if not created:
        return txn, True

    with db_transaction.atomic():

        wallet_ids = [
            from_wallet_id,
            to_wallet_id,
        ]

        wallets = (
            Wallet.objects
            .select_for_update()
            .filter(pk__in=wallet_ids)
        )

        wallets = {
            wallet.pk: wallet
            for wallet in wallets
        }

        source = wallets.get(from_wallet_id)
        destination = wallets.get(to_wallet_id)

        if source is None or destination is None:
            _fail(txn, "Wallet not found.")
            return txn, False

        if (
            source.status != WalletStatus.ACTIVE
            or destination.status != WalletStatus.ACTIVE
        ):
            _fail(txn, "One of the wallets is not active.")
            return txn, False

        if source.currency_id != destination.currency_id:
            _fail(txn, "Wallets use different currencies.")
            return txn, False

        if source.balance < amount:
            _fail(txn, "Insufficient balance.")
            return txn, False

        source.balance -= amount
        destination.balance += amount

        source.save(
            update_fields=[
                "balance",
                "updated_at",
            ]
        )

        destination.save(
            update_fields=[
                "balance",
                "updated_at",
            ]
        )

        _complete(txn)
        TransactionLedger.objects.create(
            transaction=txn,
            wallet=source,
            direction=LedgerDirection.DEBIT,
            amount=amount,
            balance_after=source.balance,
        )

        TransactionLedger.objects.create(
            transaction=txn,
            wallet=destination,
            direction=LedgerDirection.CREDIT,
            amount=amount,
            balance_after=destination.balance,
        )
        def after_commit():
            if amount >= LARGE_TRANSFER_THRESHOLD:
                from apps.transactions.tasks import notify_monitoring_team
                notify_monitoring_team.delay(txn.id)

            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"user_{destination.user_id}",
                {
                    "type": "wallet_notification",
                    "data": {
                        "idempotency_key": str(txn.idempotency_key),
                        "amount": str(txn.amount),
                        "currency": destination.currency.code,
                        "sender_wallet": str(source.id),  # اصلاح‌شده
                        "recipient_wallet": str(destination.id),  # اصلاح‌شده
                        "message": f"You received {txn.amount} {destination.currency.code}",
                    },
                },
            )

        db_transaction.on_commit(after_commit)
        return txn, False
