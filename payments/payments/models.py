from django.db import models

from django.db import models
from django.conf import settings
import uuid

class Wallet(models.Model):
    # OneToOneField means: One User = Exactly One Wallet
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='wallet'
    )
   
    # Store money as Decimal, not Float!
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    bonus = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
   
    # A unique Wallet ID (useful if you want to allow wallet-to-wallet transfers later)
    wallet_id = models.CharField(max_length=12, unique=True, blank=True, null=True)
   
    # Transaction PIN (User must enter this to buy airtime)
    # Note: In production, we should hash this like a password.
    pin = models.CharField(max_length=4, default='0000', help_text="4-digit Transaction PIN")
   
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - ₦{self.balance}"

    def save(self, *args, **kwargs):
        # Auto-generate a wallet ID if it doesn't exist
        if not self.wallet_id:
            self.wallet_id = str(uuid.uuid4().int)[:10] # Generates a random 10-digit number
        super().save(*args, **kwargs)