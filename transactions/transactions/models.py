from django.db import models

from django.db import models
from django.conf import settings
import uuid

class Transaction(models.Model):
    # Transaction Types
    TRANSACTION_TYPES = (
        ('AIRTIME', 'Airtime Topup'),
        ('DATA', 'Data Bundle'),
        ('CABLE', 'Cable TV Subscription'),
        ('ELECTRICITY', 'Electricity Bill'),
        ('FUNDING', 'Wallet Funding'),
    )

    # Status Types
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('SUCCESS', 'Successful'),
        ('FAILED', 'Failed'),
        ('REFUNDED', 'Refunded'),
    )

    # NETWORKS (You can expand this later)
    NETWORK_CHOICES = (
        ('MTN', 'MTN'),
        ('AIRTEL', 'Airtel'),
        ('GLO', 'Glo'),
        ('9MOBILE', '9mobile'),
        ('OTHERS', 'Others'),
    )

    # --- Relationships ---
    # Links the transaction to a specific user
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='transactions'
    )

    # --- Core Transaction Info ---
    # Unique ID for this specific transaction (Internal)
    transaction_id = models.CharField(max_length=100, unique=True, default=uuid.uuid4)
   
    # Reference ID from the external API (e.g., Paystack ref or ClubKonnect ID)
    reference = models.CharField(max_length=100, blank=True, null=True)
   
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    old_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    new_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    # --- Service Details ---
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    network = models.CharField(max_length=20, choices=NETWORK_CHOICES, blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    plan_code = models.CharField(max_length=50, blank=True, null=True, help_text="e.g 1GB-MTN-SME")

    # --- Status & Auditing ---
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    description = models.TextField(blank=True, null=True)
   
    # SECURITY: Store the raw response from the API provider here for debugging
    api_response = models.JSONField(default=dict, blank=True, null=True)
   
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.transaction_type} - {self.amount}"