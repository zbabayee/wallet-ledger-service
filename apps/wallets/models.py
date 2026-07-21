from django.conf import settings
from django.db import models
from django.db.models import Q

from common.constants import (
    MONEY_DECIMAL_PLACES,
    MONEY_MAX_DIGITS,
    ZERO_AMOUNT,
)
from common.models import TimeStampedUUIDModel


class WalletStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    FROZEN = "FROZEN", "Frozen"
    CLOSED = "CLOSED", "Closed"

class Currency(TimeStampedUUIDModel):
    code = models.CharField(max_length=8, unique=True)
    name = models.CharField(max_length=64)
    decimal_places = models.PositiveSmallIntegerField(default=2)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "currencies"
        ordering = ("code",)

    def __str__(self):
        return self.code





class Wallet(TimeStampedUUIDModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wallets")
    currency = models.ForeignKey(Currency,on_delete=models.PROTECT, related_name="wallets")
    label = models.CharField(max_length=100,blank=True)
    balance = models.DecimalField(max_digits=MONEY_MAX_DIGITS, decimal_places=MONEY_DECIMAL_PLACES, default=ZERO_AMOUNT)
    status = models.CharField(max_length=16, choices=WalletStatus.choices, default=WalletStatus.ACTIVE)

    class Meta:
        db_table = "wallets"

        constraints = [
            models.CheckConstraint(
                condition=Q(balance__gte=0),
                name="wallet_balance_gte_zero",
            ),
            models.UniqueConstraint(
                fields=["user", "currency"],
                condition=Q(status=WalletStatus.ACTIVE),
                name="unique_active_wallet_per_currency",
            ),
        ]

        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["user", "status"]),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.currency.code}"