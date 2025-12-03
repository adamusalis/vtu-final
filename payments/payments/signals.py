from django.db.models.signals import post_save

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from .models import Wallet

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_wallet(sender, instance, created, **kwargs):
    """
    When a User is created, automatically create a Wallet for them.
    """
    if created:
        Wallet.objects.create(user=instance)

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def save_wallet(sender, instance, **kwargs):
    """
    When a User is saved, ensure the Wallet is saved too.
    """
    instance.wallet.save()