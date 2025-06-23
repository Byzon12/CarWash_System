from django.shortcuts import render

# Create your views here.
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.db.models import Q
from .models import Tenant, Service, Booking
from .serializer import BookingSerializer
from .payment_gateways.mpesa import lipa_na_mpesa
from .payment_gateways.paypal import initiate_paypal_payment
from .payment_gateways.visa import initiate_visa_payment
from django.http import JsonResponse
from .models import Booking
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
import json



# List bookings for tenant admin, with filters
class TenantBookingList(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        tenant = getattr(request.user, 'tenant', None)
        if not tenant:
            return Response({"error": "Tenant not found"}, status=404)
        tenant_id = tenant.id
        tenant_id = request.query_params.get('tenantId', tenant_id)
        if not tenant_id:
            return Response({"error": "tenantId query parameter is required"}, status=400)
        status = request.query_params.get('status')
        staff = request.query_params.get('staff')
        start = request.query_params.get('start')
        end = request.query_params.get('end')

        bookings = Booking.objects.filter(tenant_id=tenant_id)

        if status:
            bookings = bookings.filter(status=status)
        if staff:
            bookings = bookings.filter(staff_id=staff)
        if start and end:
            bookings = bookings.filter(time_slot__range=[start, end])

        serializer = BookingSerializer(bookings, many=True)
        return Response(serializer.data)

# Update booking status
class UpdateBookingStatus(APIView):
    permission_classes = [AllowAny]

    def post(self, request, booking_id):
        status = request.data.get('status')
        if status not in dict(Booking.STATUS_CHOICES):
            return Response({"error": "Invalid status"}, status=400)

        try:
            booking = Booking.objects.get(id=booking_id)
        except Booking.DoesNotExist:
            return Response({"error": "Booking not found"}, status=404)

        booking.status = status
        booking.save()
        return Response({'status': 'updated'})

# Calendar view: aggregate bookings by staff and date
class CalendarBookingView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        tenant_id = request.query_params.get('tenantId')
        if not tenant_id:
            return Response({"error": "tenantId query parameter is required"}, status=400)

        bookings = Booking.objects.filter(tenant_id=tenant_id)
        data = {}
        for booking in bookings:
            key = f"{booking.staff_id}_{booking.time_slot.date()}"
            if key not in data:
                data[key] = []
            data[key].append(BookingSerializer(booking).data)
        return Response(data)

# Customer side: get list of services by tenant
class ServiceList(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        tenant_id = request.query_params.get('tenantId')
        if not tenant_id:
            return Response({"error": "tenantId query parameter is required"}, status=400)

        services = Service.objects.filter(tenant_id=tenant_id)
        serializer = ServiceSerializer(services, many=True)
        return Response(serializer.data)

# Customer side: check staff availability for a service and date
class StaffAvailability(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        tenant_id = request.query_params.get('tenantId')
        service_id = request.query_params.get('serviceId')
        date = request.query_params.get('date')  # YYYY-MM-DD

        if not all([tenant_id, service_id, date]):
            return Response({"error": "tenantId, serviceId, and date are required"}, status=400)

        try:
            service = Service.objects.get(id=service_id, tenant_id=tenant_id)
        except Service.DoesNotExist:
            return Response({"error": "Service not found for tenant"}, status=404)

        duration = service.duration_minutes
        slots = []

        active_staff = Staff.objects.filter(tenant_id=tenant_id, is_active=True)
        for staff in active_staff:
            # Simple availability mock — checks 9am to 5pm hourly slots
            for hour in range(9, 17):
                time_str = f"{date}T{hour:02}:00:00"
                exists = Booking.objects.filter(staff=staff, time_slot=time_str).exists()
                if not exists:
                    slots.append({
                        "staff_id": staff.id,
                        "staff_name": staff.name,
                        "time": time_str,
                    })

        return Response(slots)

# Customer creates a booking (status defaults to 'pending')
class CreateBooking(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        data = request.data.copy()

        # Ensure 'service' is provided
        service_id = data.get('service')
        if not service_id:
            return Response({'error': 'Service ID is required.'}, status=400)

        # Fetch service and price
        try:
            service = Service.objects.get(id=service_id)
            data['amount'] = service.price
        except Service.DoesNotExist:
            return Response({'error': 'Service not found.'}, status=404)

        # Serialize and save
        serializer = BookingSerializer(data=data)
        if serializer.is_valid():
            serializer.save(status='pending')
            return Response({'status': 'created', 'booking': serializer.data}, status=201)
        return Response(serializer.errors, status=400)

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
        return JsonResponse({'error': 'Booking not found'}, status=404)