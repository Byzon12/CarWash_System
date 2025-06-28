import requests
import datetime
import base64
import json
import re
from requests.auth import HTTPBasicAuth
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from booking.models import Booking

# Constants – Use environment variables in production
CONSUMER_KEY = 'rLQ2D5DBhGoyHwgrw15dGa0U0V3sUFvO0oGhjMaPpJGy7qKE'
CONSUMER_SECRET = 'LwXCBI1nRLDps9Ta5Zf1GgcQGRn5hZG50xILRwUP62DtyAGszGXy4nfxZoIMt9DY'
SHORT_CODE = '174379'
PASSKEY = 'bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919'
CALLBACK_URL = 'https://mydomain.com/api/mpesa-callback/'  # Must be HTTPS

def sanitize_phone_number(phone):
    """
    Converts Kenyan phone numbers to Safaricom MSISDN format.
    Example: 0712345678 → 254712345678
    """
    phone = str(phone).strip().replace(" ", "")
    phone = re.sub(r'\D', '', phone)

    if phone.startswith("0") and len(phone) == 10:
        return "254" + phone[1:]
    elif phone.startswith("7") and len(phone) == 9:
        return "254" + phone
    elif phone.startswith("254") and len(phone) == 12:
        return phone
    else:
        raise ValueError(f"Invalid phone number format: {phone}")

def get_access_token():
    url = 'https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials'
    try:
        response = requests.get(url, auth=HTTPBasicAuth(CONSUMER_KEY, CONSUMER_SECRET))
        response.raise_for_status()
        data = response.json()
        return data.get('access_token')
    except Exception as e:
        raise Exception(f"Access token error: {str(e)}")

def lipa_na_mpesa(phone_number, amount, reference, description):
    access_token = get_access_token()
    timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    password = base64.b64encode((SHORT_CODE + PASSKEY + timestamp).encode()).decode()

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    # ✅ Sanitize the phone number
    phone = sanitize_phone_number(phone_number)

    payload = {
        "BusinessShortCode": SHORT_CODE,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": int(amount),
        "PartyA": phone,
        "PartyB": SHORT_CODE,
        "PhoneNumber": phone,
        "CallBackURL": CALLBACK_URL,
        "AccountReference": reference,
        "TransactionDesc": description
    }

    response = requests.post(
        'https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest',
        headers=headers,
        json=payload
    )
    return response.json()

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
                booking = Booking.objects.get(payment_reference=checkout_request_id)
                booking.payment_status = 'paid'
                booking.status = 'confirmed'
                booking.save()
                print(f"[✅ PAID] Booking {booking.id}: KES {amount} by {phone}")
            except Booking.DoesNotExist:
                print(f"[⚠️ NOT FOUND] Booking with CheckoutRequestID {checkout_request_id} not found")

        else:
            print(f"[❌ FAILED] ResultCode: {result_code}, CheckoutRequestID: {checkout_request_id}")

    except Exception as e:
        print("Callback error:", str(e))

    return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})
