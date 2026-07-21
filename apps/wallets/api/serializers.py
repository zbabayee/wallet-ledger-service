from rest_framework import serializers

from apps.wallets.models import Currency, Wallet


class CurrencyMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Currency
        fields = [
            "id",
            "code",
            "name",
            "decimal_places"
        ]


class WalletSerializer(serializers.ModelSerializer):
    currency = CurrencyMiniSerializer(read_only=True)

    class Meta:
        model = Wallet
        fields = [
            "id",
            "currency",
            "label",
            "balance",
            "status",
            "created_at"
        ]
        read_only_fields = fields


class WalletCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = [
            "id",
            "currency",
            "label"
        ]

    def validate_currency(self, currency):
        if not currency.is_active:
            raise serializers.ValidationError("This currency is not active.")
        return currency
