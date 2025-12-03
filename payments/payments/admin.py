from django.contrib import admin

from django.contrib import admin
from .models import Wallet

@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance', 'wallet_id', 'updated_at')
    search_fields = ('user__username', 'wallet_id')