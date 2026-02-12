from decouple import config
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django_daraja.mpesa.core import MpesaClient
from .models import MpesaTransaction
import logging

# Get an instance of a logger
logger = logging.getLogger(__name__)

class InitiateSTKPushView(APIView):
    """
    Step 1: Send the payment prompt to the user's phone.
    """
    def post(self, request):
        phone_number = request.data.get('phone_number')
        amount = request.data.get('amount')
        
        cl = MpesaClient()
        
        
        # IN DEV: Use your Ngrok URL
        # IN PROD: Use your live domain
        base_url = config("BASE_URL").rstrip("/")
        callback_url = f"{base_url}/api/callback/"
        
        logger.info(f"Initiating STK Push for {phone_number} amount: KES {amount}")

        try:
            response = cl.stk_push(phone_number, amount, "TestAccount", "Payment", callback_url)
            
            if response.response_code == "0":
                # O(1) Write
                MpesaTransaction.objects.create(
                    checkout_request_id=response.checkout_request_id,
                    phone_number=phone_number,
                    amount=amount,
                    status='PENDING'
                )
                logger.info(f"STK Push successful. CheckoutID: {response.checkout_request_id}")
                return Response(response.json(), status=status.HTTP_200_OK)
            else:
                logger.warning(f"STK Push failed: {response.error_message}")
                return Response(response.json(), status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"STK Push Error: {str(e)}", exc_info=True)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MpesaCallbackView(APIView): 
    """
    Step 2: Safaricom sends data back here.
    
    """
    def get(self, request):
        return Response({"status": "Callback URL is active. Waiting for POST data."}, status=status.HTTP_200_OK)
    
    def post(self, request):
        data = request.data
        
        logger.info(f"Callback Received: {data}")
        
        try:
            # 1. Extract Identifiers
            stk_callback = data.get('Body', {}).get('stkCallback', {})
            checkout_request_id = stk_callback.get('CheckoutRequestID')
            result_code = stk_callback.get('ResultCode')
            result_desc = stk_callback.get('ResultDesc')

            # 2. Database Lookup (O(log n))
            transaction = MpesaTransaction.objects.get(checkout_request_id=checkout_request_id)

            if result_code == 0:
                # 3. Success: Parse Metadata
                items = stk_callback.get('CallbackMetadata', {}).get('Item', [])
                
                mpesa_receipt = None
                for item in items:
                    if item.get('Name') == 'MpesaReceiptNumber':
                        mpesa_receipt = item.get('Value')
                        break

                transaction.status = 'COMPLETED'
                transaction.transaction_id = mpesa_receipt
                transaction.result_desc = 'Payment Successful'
                logger.info(f"Payment Completed for {checkout_request_id}. Ref: {mpesa_receipt}")
            else:
                # 4. Failure
                transaction.status = 'FAILED'
                transaction.result_desc = result_desc
                logger.warning(f"Payment Failed for {checkout_request_id}: {result_desc}")

            # 5. Save Changes
            transaction.save()

        except MpesaTransaction.DoesNotExist:
            logger.error(f"CRITICAL: Transaction with ID {checkout_request_id} not found in DB.")
        except Exception as e:
            logger.error(f"Error processing callback: {e}", exc_info=True)

        # 6. Return Success to Safaricom
        return Response({"ResultCode": 0, "ResultDesc": "Accepted"}, status=status.HTTP_200_OK)