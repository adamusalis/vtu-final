from rest_framework import serializers
from .models import Transaction

class AirtimePurchaseSerializer(serializers.Serializer):
    network = serializers.ChoiceField(choices=Transaction.NETWORK_CHOICES)
    phone_number = serializers.CharField(max_length=15)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)

    def validate_amount(self, value):
        """Ensure amount is positive."""
        if value <= 0:
            raise serializers.ValidationError("Amount must be positive.")
        return value