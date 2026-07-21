from rest_framework import serializers

from apps.wallets.models import Wallet


class WalletMinimalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = [
            "id",
            "label",
            "balance",
            "status",
        ]
        read_only_fields = fields
