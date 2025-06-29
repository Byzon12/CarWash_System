from django.shortcuts import render

# Create your views here.
from rest_framework.views import APIView
from rest_framework import status, generics, serializers
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.db.models import Q
from .models import Tenant, Service, Booking, CustomerProfile
from .serializer import BookingCreateSerializer
from .payment_gateways.mpesa import lipa_na_mpesa
from .payment_gateways.paypal import initiate_paypal_payment
from .payment_gateways.visa import initiate_visa_payment
from django.http import JsonResponse
from .models import Booking
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
import json

class BookingCreateView(generics.CreateAPIView):
    """
    Create a new booking for a customer.
    The booking is associated with the tenant of the authenticated user.
    The customer is automatically set to the authenticated user's profile.
    """
    serializer_class = BookingCreateSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        customer_profile = self.request.user.Customer_profile
        return Booking.objects.filter(customer=customer_profile).order_by('-created_at')

    def perform_create(self, serializer):
        user = self.request.user
        # Safely get customer profile
        try:
            customer_profile = user.Customer_profile
        except CustomerProfile.DoesNotExist:
            raise serializers.ValidationError({"error": "No CustomerProfile associated with this user."})

        serializer.save(customer=customer_profile)




"""

@csrf_exempt
def initiate_payment(request):
    if request.method == 'POST':
        print("Headers:", request.headers)
        print("Raw body:", request.body.decode('utf-8'))

        try:
            data = json.loads(request.body.decode('utf-8'))
        except json.JSONDecodeError as e:
            return JsonResponse({'error': f'Invalid or missing JSON: {str(e)}'}, status=400)

        booking_id = data.get('booking_id')
        payment_method = data.get('method')

        if not booking_id or not payment_method:
            return JsonResponse({'error': 'booking_id and method are required'}, status=400)

        booking = get_object_or_404(Booking, id=booking_id)

        if payment_method == 'mpesa':
            response = lipa_na_mpesa(
                str(booking.phone_number),
                float(booking.amount),
                f"Booking{booking.id}",
                "Car Wash Booking"
            )

            # ✅ Save the CheckoutRequestID for callback matching
            checkout_id = response.get('CheckoutRequestID')
            if checkout_id:
                booking.payment_reference = checkout_id
                booking.payment_method = 'mpesa'
                booking.payment_status = 'pending'
                booking.save()

        elif payment_method == 'paypal':
            response = initiate_paypal_payment(booking)
        elif payment_method == 'visa':
            response = initiate_visa_payment(booking)
        else:
            return JsonResponse({'error': 'Invalid payment method'}, status=400)

        return JsonResponse({'message': 'Payment initiated', 'data': response})

    return JsonResponse({'error': 'Invalid request method'}, status=405)


@csrf_exempt
def mpesa_callback(request):
    try:
        data = json.loads(request.body.decode('utf-8'))
        result = data['Body']['stkCallback']
        result_code = result.get('ResultCode')
        merchant_request_id = result.get('MerchantRequestID')
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
                # ✅ Update booking using the reference stored earlier
                booking = Booking.objects.get(payment_reference=checkout_request_id)
                booking.payment_status = 'paid'
                booking.status = 'confirmed'
                booking.save()
                print(f"[✅ PAID] Booking {booking.id}: KES {amount} from {phone}")
            except Booking.DoesNotExist:
                print(f"[⚠️ Booking Not Found] for CheckoutRequestID: {checkout_request_id}")

        else:
            print(f"[❌ FAILED] Payment failed. Result code: {result_code}. Request ID: {merchant_request_id}")

    except Exception as e:
        print("Callback processing error:", str(e))

    return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})


@csrf_exempt
def payment_callback(request):
    try:
        data = json.loads(request.body.decode('utf-8'))
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    booking_id = data.get('booking_id')
    status = data.get('status')  # 'success' or 'failed'
    reference = data.get('reference', '')

    try:
        booking = Booking.objects.get(id=booking_id)
        booking.payment_status = 'paid' if status == 'success' else 'failed'
        booking.status = 'confirmed' if status == 'success' else 'pending'
        booking.payment_reference = reference
        booking.save()
        return JsonResponse({'message': 'Payment updated successfully'})
    except Booking.DoesNotExist:
        return JsonResponse({'error': 'Booking not found'}, status=404)"""