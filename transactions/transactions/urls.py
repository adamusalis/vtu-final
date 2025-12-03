from django.urls import path
from .views import BuyAirtimeView

urlpatterns = [
    path('buy-airtime/', BuyAirtimeView.as_view(), name='buy-airtime'),
]