import requests
import datetime
import base64
import json
import re
import logging
from requests.auth import HTTPBasicAuth
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from booking.models import booking

logger = logging.getLogger(__name__)

class MpesaConfig:
    """M-Pesa configuration - use environment variables in production"""
    CONSUMER_KEY = getattr(settings, 'MPESA_CONSUMER_KEY', 'rLQ2D5DBhGoyHwgrw15dGa0U0V3sUFvO0oGhjMaPpJGy7qKE')
    CONSUMER_SECRET = getattr(settings, 'MPESA_CONSUMER_SECRET', 'LwXCBI1nRLDps9Ta5Zf1GgcQGRn5hZG50xILRwUP62DtyAGszGXy4nfxZoIMt9DY')
    SHORT_CODE = getattr(settings, 'MPESA_SHORT_CODE', '174379')
    PASSKEY = getattr(settings, 'MPESA_PASSKEY', 'bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919')
    CALLBACK_URL = getattr(settings, 'MPESA_CALLBACK_URL', 'https://your-domain.com/api/booking/mpesa-callback/')
    ENVIRONMENT = getattr(settings, 'MPESA_ENVIRONMENT', 'sandbox')  # 'sandbox' or 'production'
    
    @property
    def base_url(self):
        if self.ENVIRONMENT == 'production':
            return 'https://api.safaricom.co.ke'
        return 'https://sandbox.safaricom.co.ke'

class MpesaService:
    def __init__(self):
        self.config = MpesaConfig()
    
    def sanitize_phone_number(self, phone):
        """Convert Kenyan phone numbers to Safaricom MSISDN format"""
        phone = str(phone).strip().replace(" ", "").replace("-", "")
        phone = re.sub(r'\D', '', phone)

        if phone.startswith("0") and len(phone) == 10:
            return "254" + phone[1:]
        elif phone.startswith("7") and len(phone) == 9:
            return "254" + phone
        elif phone.startswith("254") and len(phone) == 12:
            return phone
        else:
            raise ValueError(f"Invalid phone number format: {phone}")

    def get_access_token(self):
        """Get OAuth access token from Safaricom"""
        url = f'{self.config.base_url}/oauth/v1/generate?grant_type=client_credentials'
        try:
            response = requests.get(
                url, 
                auth=HTTPBasicAuth(self.config.CONSUMER_KEY, self.config.CONSUMER_SECRET),
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            access_token = data.get('access_token')
            
            if not access_token:
                raise Exception("No access token in response")
                
            logger.info("Successfully obtained M-Pesa access token")
            return access_token
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get M-Pesa access token: {str(e)}")
            raise Exception(f"Access token error: {str(e)}")

    def initiate_stk_push(self, phone_number, amount, booking_reference, description="Car Wash Booking"):
        """Initiate M-Pesa STK Push payment"""
        try:
            access_token = self.get_access_token()
            timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
            password = base64.b64encode(
                (self.config.SHORT_CODE + self.config.PASSKEY + timestamp).encode()
            ).decode()

            # Sanitize phone number
            phone = self.sanitize_phone_number(phone_number)
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }

            payload = {
                "BusinessShortCode": self.config.SHORT_CODE,
                "Password": password,
                "Timestamp": timestamp,
                "TransactionType": "CustomerPayBillOnline",
                "Amount": int(float(amount)),
                "PartyA": phone,
                "PartyB": self.config.SHORT_CODE,
                "PhoneNumber": phone,
                "CallBackURL": self.config.CALLBACK_URL,
                "AccountReference": booking_reference,
                "TransactionDesc": description
            }

            url = f'{self.config.base_url}/mpesa/stkpush/v1/processrequest'
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response_data = response.json()
            
            logger.info(f"M-Pesa STK Push initiated for {booking_reference}: {response_data}")
            
            return {
                'success': response.status_code == 200,
                'response_code': response_data.get('ResponseCode'),
                'response_description': response_data.get('ResponseDescription'),
                'checkout_request_id': response_data.get('CheckoutRequestID'),
                'merchant_request_id': response_data.get('MerchantRequestID'),
                'customer_message': response_data.get('CustomerMessage'),
                'raw_response': response_data
            }
            
        except Exception as e:
            logger.error(f"M-Pesa STK Push failed for {booking_reference}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'response_description': 'Payment initiation failed'
            }

    def query_transaction_status(self, checkout_request_id):
        """Query the status of an M-Pesa transaction"""
        try:
            access_token = self.get_access_token()
            timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
            password = base64.b64encode(
                (self.config.SHORT_CODE + self.config.PASSKEY + timestamp).encode()
            ).decode()
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }

            payload = {
                "BusinessShortCode": self.config.SHORT_CODE,
                "Password": password,
                "Timestamp": timestamp,
                "CheckoutRequestID": checkout_request_id
            }

            url = f'{self.config.base_url}/mpesa/stkpushquery/v1/query'
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response_data = response.json()
            
            return {
                'success': response.status_code == 200,
                'result_code': response_data.get('ResultCode'),
                'result_desc': response_data.get('ResultDesc'),
                'raw_response': response_data
            }
            
        except Exception as e:
            logger.error(f"M-Pesa transaction query failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

# Singleton instance
mpesa_service = MpesaService()

@csrf_exempt
def mpesa_callback(request):
    try:
        data = json.loads(request.body.decode('utf-8'))
        result = data['Body']['stkCallback']
        result_code = result.get('ResultCode')
        checkout_request_id = result.get('CheckoutRequestID')

        if result_code == 0:
            metadata = result.get('CallbackMetadata', {}).get('Item', [])
            phone = None
            amount = None

            for item in metadata:
                if item['Name'] == 'PhoneNumber':
                    phone = item['Value']
                elif item['Name'] == 'Amount':
                    amount = item['Value']

            try:
                booking = booking.objects.get(payment_reference=checkout_request_id)
                booking.payment_status = 'paid'
                booking.status = 'confirmed'
                booking.save()
                print(f"[✅ PAID] Booking {booking.id}: KES {amount} by {phone}")
            except booking.DoesNotExist:
                print(f"[⚠️ NOT FOUND] Booking with CheckoutRequestID {checkout_request_id} not found")

        else:
            print(f"[❌ FAILED] ResultCode: {result_code}, CheckoutRequestID: {checkout_request_id}")

    except Exception as e:
        print("Callback error:", str(e))

    return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})
