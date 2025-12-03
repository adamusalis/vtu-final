from rest_framework.views import APIView

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db import transaction
import uuid

from .models import Wallet
from transactions.models import Transaction
# Ensure FundWalletSerializer is imported here:
from .serializers import WalletSerializer, FundWalletSerializer

class WalletBalanceView(APIView):
    # SECURITY: Only logged-in users can access this!
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # 1. Get the logged-in user
        user = request.user
       
        # 2. Find their specific wallet
        # (We use try/except just in case the signal failed earlier)
        try:
            wallet = Wallet.objects.get(user=user)
            serializer = WalletSerializer(wallet)
            return Response(serializer.data)
        except Wallet.DoesNotExist:
            return Response({"error": "Wallet not found"}, status=404)

class InitializeFundingView(APIView):
    """
    User says "I want to deposit 5000".
    We create a PENDING Funding transaction and give them a reference ID.
    They take this reference ID to Paystack/Monnify to make the actual payment.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = FundWalletSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        amount = serializer.validated_data['amount']
        user = request.user

        # Generate a unique reference for this deposit attempt
        # Format: FUND-{user_id}-{random_string}
        ref = f"FUND-{user.id}-{uuid.uuid4().hex[:8].upper()}"

        # Create a PENDING transaction record so we know they are trying to pay
        Transaction.objects.create(
            user=user,
            transaction_id=ref, # Using our generated ref as the main ID here
            transaction_type='FUNDING',
            amount=amount,
            status='PENDING',
            description=f"Wallet funding attempt of ₦{amount}"
        )

        # Return the reference to the frontend.
        # The frontend will use this reference when opening the Paystack popup.
        return Response({
            "status": "success",
            "message": "Funding initialized",
            "reference": ref,
            "amount": amount,
            "email": user.email
        })
    
class FundingWebhookView(APIView):
    """
    This endpoint is called by the Payment Gateway (e.g., Paystack)
    when a payment is successful. It is NOT called by a user.
    """
    # IMPORTANT: Gateways don't log in, so we allow any connection.
    # IN PRODUCTION: You MUST verify the signature header to ensure the request
    # actually came from Paystack and not a hacker. We skip that for now.
    permission_classes = [AllowAny]

    def post(self, request):
        # 1. Simulate getting data from gateway.
        # In reality, Paystack sends a big JSON object. We just need the reference.
        # Let's assume they send: {"event": "charge.success", "data": {"reference": "..."}}
       
        gateway_data = request.data.get('data', {})
        reference = gateway_data.get('reference')
        status = gateway_data.get('status')

        if not reference or status != 'success':
             # Ignore incomplete or failed notifications
            return Response({"status": "ignored"}, status=200)

        try:
            # 2. Find the PENDING transaction
            with transaction.atomic():
                trx = Transaction.objects.select_for_update().get(
                    transaction_id=reference,
                    status='PENDING',
                    transaction_type='FUNDING'
                )

                # 3. Find the user's wallet
                wallet = Wallet.objects.select_for_update().get(user=trx.user)

                # 4. Add money & update records
                old_balance = wallet.balance
                new_balance = wallet.balance + trx.amount
               
                wallet.balance = new_balance
                wallet.save()

                trx.status = 'SUCCESS'
                trx.old_balance = old_balance
                trx.new_balance = new_balance
                # Save the raw data from gateway for debugging
                trx.api_response = request.data
                trx.save()

                print(f"Webhook Success: Funded {trx.amount} for ref {reference}")
                # Always return 200 OK to the gateway immediately
                return Response({"status": "processed"}, status=200)

        except Transaction.DoesNotExist:
            # Transaction already processed or invalid ref
            print(f"Webhook Error: Invalid ref {reference}")
            return Response({"status": "invalid_reference"}, status=200)
        except Exception as e:
            print(f"Webhook Critical Error: {e}")
            # Gateways usually retry if you send a 500 error
            return Response({"status": "error"}, status=500)