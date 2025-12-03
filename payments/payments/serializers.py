from rest_framework import serializers

from rest_framework import serializers
from .models import Wallet

class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        # We only show them safe info. Never expose internal IDs if not needed.
        fields = ['wallet_id', 'balance', 'bonus', 'updated_at']
        # ... (keep existing WalletSerializer at the top)

# ... (keep existing WalletSerializer at the top)

class FundWalletSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)

    def validate_amount(self, value):
        if value < 100: # Minimum funding amount
            raise serializers.ValidationError("Minimum funding amount is ₦100.")
        return value