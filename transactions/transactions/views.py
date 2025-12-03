from rest_framework.views import APIView

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from payments.models import Wallet
from .models import Transaction
from .serializers import AirtimePurchaseSerializer
# Import our new mock vendor service
from .services import RealVTUVendor

class BuyAirtimeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # 1. Validate data
        serializer = AirtimePurchaseSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        amount = serializer.validated_data['amount']
        network = serializer.validated_data['network']
        phone_number = serializer.validated_data['phone_number']
        user = request.user

        # Initialize vendor
        vendor = RealVTUVendor()

        try:
            # === DATABASE TRANSACTION START ===
            # We wrap everything to ensure money isn't lost if code crashes halfway
            with transaction.atomic():
                # a. Lock & Get Wallet
                wallet = Wallet.objects.select_for_update().get(user=user)

                # b. Check Balance
                if wallet.balance < amount:
                    return Response({"error": "Insufficient funds"}, status=400)

                # c. Deduct Money (Temporarily)
                old_balance = wallet.balance
                new_balance = wallet.balance - amount
                wallet.balance = new_balance
                wallet.save()

                # d. Create PENDING Transaction Record
                trx = Transaction.objects.create(
                    user=user,
                    transaction_type='AIRTIME',
                    amount=amount,
                    old_balance=old_balance,
                    new_balance=new_balance,
                    network=network,
                    phone_number=phone_number,
                    status='PENDING',
                    description=f"Airtime purchase of ₦{amount} for {phone_number}"
                )
               
                # === CALL VENDOR API (The dangerous part) ===
                # Note: In production, this should often be done outside the atomic block via Celery tasks.
                # For now, we do it here to keep it simple.
                vendor_response = vendor.purchase_airtime(network, phone_number, amount, trx.transaction_id)

                # e. Handle Vendor Response
                if vendor_response['status'] == 'success':
                    # Mark successful
                    trx.status = 'SUCCESS'
                    trx.reference = vendor_response['vendor_reference']
                    trx.api_response = vendor_response['raw_response']
                    trx.save()
                   
                    response_data = {
                        "status": "success",
                        "message": "Airtime delivered successfully",
                        "transaction_id": trx.transaction_id,
                        "new_balance": wallet.balance
                    }
                    status_code = 200

                else:
                    # VENDOR FAILED - REFUND THE USER!
                    wallet.balance = old_balance # Give money back
                    wallet.save()
                   
                    trx.status = 'FAILED'
                    trx.description = f"Failed: {vendor_response['message']}"
                    trx.api_response = vendor_response['raw_response']
                    # Update new_balance in record to show refund happened
                    trx.new_balance = old_balance
                    trx.save()

                    response_data = {
                        "status": "failed",
                        "message": vendor_response['message'],
                        "transaction_id": trx.transaction_id,
                        "new_balance": wallet.balance # Balance is restored
                    }
                    status_code = 400 # Or 503 depending on preference

            # === DATABASE TRANSACTION END ===
            return Response(response_data, status=status_code)

        except Wallet.DoesNotExist:
            return Response({"error": "User has no wallet"}, status=400)
        except Exception as e:
            # Unexpected crash - transaction block will auto-rollback changes
            print(f"Critical Error: {str(e)}")
            return Response({"error": "An unexpected error occurred"}, status=500)