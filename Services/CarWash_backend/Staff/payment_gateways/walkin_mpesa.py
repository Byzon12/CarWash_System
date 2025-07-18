import json
import logging
from decimal import Decimal
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.utils import timezone
from ..models import WalkInCustomer, WalkInPayment
from booking.payment_gateways.mpesa import MpesaService

logger = logging.getLogger(__name__)

class WalkInMpesaService(MpesaService):
    """Extended M-Pesa service specifically for walk-in customers."""
    
    def __init__(self):
        super().__init__()
        # Override callback URL for walk-in customers
        self.config.CALLBACK_URL = getattr(
            self.config, 
            'WALKIN_MPESA_CALLBACK_URL', 
            'https://your-domain.com/api/staff/walkin-customers/mpesa-callback/'
        )
    
    def initiate_walkin_payment(self, walkin_customer_id, phone_number, amount, description="Walk-in Car Wash Service"):
        """Initiate M-Pesa STK Push payment for walk-in customer."""
        try:
            # Get walk-in customer
            walkin_customer = WalkInCustomer.objects.get(id=walkin_customer_id)
            
            # Create payment reference
            payment_reference = f"WALKIN-{walkin_customer.id}-{timezone.now().strftime('%Y%m%d%H%M%S')}"
            
            # Create payment record
            payment = WalkInPayment.objects.create(
                walkin_customer=walkin_customer,
                amount=Decimal(str(amount)),
                payment_method='mpesa',
                payment_reference=payment_reference,
                phone_number=self.sanitize_phone_number(phone_number),
                status='pending'
            )
            
            # Initiate STK push using parent class method
            response = self.initiate_stk_push(
                phone_number=phone_number,
                amount=amount,
                booking_reference=payment_reference,
                description=description
            )
            
            if response.get('success'):
                # Update payment with M-Pesa details
                payment.checkout_request_id = response.get('checkout_request_id')
                payment.merchant_request_id = response.get('merchant_request_id')
                payment.mpesa_response = response.get('raw_response')
                payment.save()
                
                # Update walk-in customer status
                walkin_customer.payment_status = 'processing'
                walkin_customer.save()
                
                logger.info(f"M-Pesa payment initiated for walk-in customer {walkin_customer_id}")
                
                return {
                    'success': True,
                    'payment_id': payment.id,
                    'checkout_request_id': response.get('checkout_request_id'),
                    'customer_message': response.get('customer_message'),
                    'payment_reference': payment_reference
                }
            else:
                # Update payment status on failure
                payment.status = 'failed'
                payment.failure_reason = response.get('response_description')
                payment.save()
                
                return {
                    'success': False,
                    'error': response.get('response_description'),
                    'payment_id': payment.id
                }
                
        except WalkInCustomer.DoesNotExist:
            logger.error(f"Walk-in customer {walkin_customer_id} not found")
            return {
                'success': False,
                'error': 'Walk-in customer not found'
            }
        except Exception as e:
            logger.error(f"M-Pesa payment initiation failed for walk-in customer {walkin_customer_id}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def query_walkin_payment_status(self, payment_id):
        """Query the status of a walk-in customer payment."""
        try:
            payment = WalkInPayment.objects.get(id=payment_id)
            
            if not payment.checkout_request_id:
                return {
                    'success': False,
                    'error': 'No checkout request ID found'
                }
            
            # Query M-Pesa transaction status
            response = self.query_transaction_status(payment.checkout_request_id)
            
            if response.get('success'):
                result_code = response.get('result_code')
                
                # Update payment status based on M-Pesa response
                if result_code == 0:
                    payment.status = 'completed'
                    payment.walkin_customer.payment_status = 'paid'
                    payment.walkin_customer.save()
                elif result_code == 1032:
                    payment.status = 'cancelled'
                elif result_code == 1:
                    payment.status = 'failed'
                else:
                    payment.status = 'pending'
                
                payment.mpesa_query_response = response.get('raw_response')
                payment.save()
                
                return {
                    'success': True,
                    'payment_status': payment.status,
                    'result_code': result_code,
                    'result_desc': response.get('result_desc')
                }
            else:
                return response
                
        except WalkInPayment.DoesNotExist:
            return {
                'success': False,
                'error': 'Payment not found'
            }
        except Exception as e:
            logger.error(f"Payment status query failed for payment {payment_id}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

# Singleton instance
walkin_mpesa_service = WalkInMpesaService()

@csrf_exempt
def walkin_mpesa_callback(request):
    """Handle M-Pesa callback for walk-in customer payments."""
    try:
        data = json.loads(request.body.decode('utf-8'))
        result = data['Body']['stkCallback']
        result_code = result.get('ResultCode')
        checkout_request_id = result.get('CheckoutRequestID')
        
        logger.info(f"Received M-Pesa callback for walk-in payment: {checkout_request_id}")
        
        # Find the payment record
        try:
            payment = WalkInPayment.objects.get(checkout_request_id=checkout_request_id)
        except WalkInPayment.DoesNotExist:
            logger.error(f"Walk-in payment with CheckoutRequestID {checkout_request_id} not found")
            return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})
        
        if result_code == 0:
            # Payment successful
            metadata = result.get('CallbackMetadata', {}).get('Item', [])
            transaction_id = None
            phone = None
            amount = None
            
            for item in metadata:
                if item['Name'] == 'MpesaReceiptNumber':
                    transaction_id = item['Value']
                elif item['Name'] == 'PhoneNumber':
                    phone = item['Value']
                elif item['Name'] == 'Amount':
                    amount = item['Value']
            
            # Update payment record
            payment.status = 'completed'
            payment.transaction_id = transaction_id
            payment.completed_at = timezone.now()
            payment.callback_response = data
            payment.save()
            
            # Update walk-in customer
            walkin_customer = payment.walkin_customer
            walkin_customer.payment_status = 'paid'
            walkin_customer.save()
            
            logger.info(f"[✅ PAID] Walk-in customer {walkin_customer.id}: KES {amount} by {phone}")
            
        else:
            # Payment failed or cancelled
            payment.status = 'failed' if result_code == 1 else 'cancelled'
            payment.failure_reason = result.get('ResultDesc')
            payment.callback_response = data
            payment.save()
            
            logger.info(f"[❌ FAILED] Walk-in payment {payment.id}: ResultCode {result_code}")
        
    except Exception as e:
        logger.error(f"Walk-in M-Pesa callback error: {str(e)}")
    
    return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})