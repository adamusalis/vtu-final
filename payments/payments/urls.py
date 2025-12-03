from django.urls import path
# Make sure all three views are imported!
from .views import WalletBalanceView, InitializeFundingView, FundingWebhookView

urlpatterns = [
    path('balance/', WalletBalanceView.as_view(), name='wallet-balance'),
    path('fund/initialize/', InitializeFundingView.as_view(), name='fund-initialize'),
    # This is the line that is likely missing or broken:
    path('fund/webhook/', FundingWebhookView.as_view(), name='fund-webhook'),
]