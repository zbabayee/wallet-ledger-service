import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q

from common.constants import (
    MONEY_DECIMAL_PLACES,
    MONEY_MAX_DIGITS,
)
from common.models import TimeStampedUUIDModel


class TransactionType(models.TextChoices):
    DEPOSIT = "DEPOSIT", "Deposit"
    WITHDRAW = "WITHDRAW", "Withdraw"
    TRANSFER = "TRANSFER", "Transfer"


class TransactionStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    PROCESSING = "PROCESSING", "Processing"
    COMPLETED = "COMPLETED", "Completed"
    FAILED = "FAILED", "Failed"


class LedgerDirection(models.TextChoices):
    CREDIT = "CREDIT", "Credit"
    DEBIT = "DEBIT", "Debit"


class Transaction(TimeStampedUUIDModel):
    idempotency_key = models.UUIDField(default=uuid.uuid4,unique=True)
    reference_number = models.CharField(max_length=64, unique=True)
    transaction_type = models.CharField(max_length=16, choices=TransactionType.choices)

    from_wallet = models.ForeignKey(
        "wallets.Wallet",
        on_delete=models.PROTECT,
        related_name="outgoing_transactions",
        null=True,
        blank=True,
    )
    to_wallet = models.ForeignKey(
        "wallets.Wallet",
        on_delete=models.PROTECT,
        related_name="incoming_transactions",
        null=True,
        blank=True)

    amount = models.DecimalField(max_digits=MONEY_MAX_DIGITS, decimal_places=MONEY_DECIMAL_PLACES)
    status = models.CharField(max_length=20, choices=TransactionStatus.choices, default=TransactionStatus.PENDING)
    description = models.CharField(max_length=255, blank=True)
    failure_reason = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="transactions")
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "transactions"

        constraints = [
            models.CheckConstraint(
                condition=Q(amount__gt=0),
                name="transaction_amount_gt_zero",
            ),
            models.CheckConstraint(
                condition=(
                    Q(transaction_type=TransactionType.DEPOSIT, from_wallet__isnull=True)
                    |
                    Q(transaction_type=TransactionType.WITHDRAW, to_wallet__isnull=True)
                    |
                    Q(transaction_type=TransactionType.TRANSFER)
                ),
                name="transaction_wallet_consistency",
            ),
        ]

        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["transaction_type"]),
            models.Index(fields=["completed_at"]),
            models.Index(fields=["created_by", "created_at"]),
        ]

    def __str__(self):
        return self.reference_number


class TransactionLedger(TimeStampedUUIDModel):
    transaction = models.ForeignKey(Transaction, on_delete=models.PROTECT, related_name="entries",)
    wallet = models.ForeignKey("wallets.Wallet", on_delete=models.PROTECT, related_name="ledger_entries")
    direction = models.CharField(max_length=10, choices=LedgerDirection.choices)
    amount = models.DecimalField(max_digits=MONEY_MAX_DIGITS, decimal_places=MONEY_DECIMAL_PLACES)
    balance_after = models.DecimalField(max_digits=MONEY_MAX_DIGITS, decimal_places=MONEY_DECIMAL_PLACES)

    class Meta:
        db_table = "transaction_ledger"

        constraints = [
            models.CheckConstraint(
                condition=Q(amount__gt=0),
                name="ledger_amount_gt_zero",
            ),
        ]

        indexes = [
            models.Index(fields=["transaction"]),
            models.Index(fields=["wallet", "created_at"]),
        ]

    def save(self, *args, **kwargs):
        if self.pk:
            raise RuntimeError("Ledger entries are immutable.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise RuntimeError("Ledger entries are immutable.")

    def __str__(self):
        return f"{self.transaction.reference_number} - {self.wallet_id}"