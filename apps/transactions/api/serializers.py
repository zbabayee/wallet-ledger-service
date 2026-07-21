from decimal import Decimal

from rest_framework import serializers

from apps.transactions.models import Transaction
from apps.wallets.models import Wallet
from apps.wallets.services.serializers import WalletMinimalSerializer

MIN_AMOUNT = Decimal("0.00000001")


class BaseWalletSerializer(serializers.Serializer):
    wallet = serializers.PrimaryKeyRelatedField(
        queryset=Wallet.objects.select_related("currency", "user")
    )
    amount = serializers.DecimalField(
        max_digits=20,
        decimal_places=8,
        min_value=MIN_AMOUNT,
    )
    idempotency_key = serializers.CharField(max_length=128)
    description = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        default="",
    )

    def validate_wallet(self, wallet):
        request = self.context["request"]

        if wallet.user_id != request.user.pk:
            raise serializers.ValidationError(
                "You do not own this wallet."
            )

        return wallet


class DepositSerializer(BaseWalletSerializer):
    pass


class WithdrawSerializer(BaseWalletSerializer):
    pass


class TransferSerializer(serializers.Serializer):
    from_wallet = serializers.PrimaryKeyRelatedField(
        queryset=Wallet.objects.select_related("currency", "user")
    )
    to_wallet = serializers.PrimaryKeyRelatedField(
        queryset=Wallet.objects.select_related("currency", "user")
    )
    amount = serializers.DecimalField(
        max_digits=20,
        decimal_places=8,
        min_value=MIN_AMOUNT,
    )
    idempotency_key = serializers.CharField(max_length=128)
    description = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        default="",
    )

    def validate_from_wallet(self, wallet):
        request = self.context["request"]

        if wallet.user_id != request.user.pk:
            raise serializers.ValidationError(
                "You do not own the source wallet."
            )

        return wallet

    def validate(self, attrs):
        if attrs["from_wallet"].pk == attrs["to_wallet"].pk:
            raise serializers.ValidationError(
                "Source and destination wallets must differ."
            )

        if (
                attrs["from_wallet"].currency_id
                != attrs["to_wallet"].currency_id
        ):
            raise serializers.ValidationError(
                "Both wallets must use the same currency."
            )

        return attrs


class TransactionSerializer(serializers.ModelSerializer):
    from_wallet = WalletMinimalSerializer(read_only=True)
    to_wallet = WalletMinimalSerializer(read_only=True)

    class Meta:
        model = Transaction
        fields = [
            "id",
            "transaction_type",
            "from_wallet",
            "to_wallet",
            "amount",
            "description",
            "status",
            "failure_reason",
            "created_at",
            "updated_at",
            "completed_at",
        ]
        read_only_fields = fields
