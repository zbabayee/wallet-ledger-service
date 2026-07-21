from rest_framework import serializers

from wallets.api.serializers import CurrencyMiniSerializer
from wallets.models import Wallet


class WalletMinimalSerializer(serializers.ModelSerializer):
    currency = CurrencyMiniSerializer(read_only=True)

    class Meta:
        model = Wallet
        fields = [
            "id",
            "label",
            "balance",
            "status",
        ]
        read_only_fields = fields
