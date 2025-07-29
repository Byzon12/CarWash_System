from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
import json
import logging

from .models import booking, BookingStatusHistory, PaymentTransaction
from .serializer import (
    BookingCreateSerializer, 
    BookingDetailSerializer, 
    BookingUpdateSerializer,
    FlutterBookingCreateSerializer,  # Add this import
    PaymentInitiationSerializer,
    PaymentInitiationURLSerializer,
    PaymentStatusSerializer,
)

from .payment_gateways.mpesa import mpesa_service

logger = logging.getLogger(__name__)

class BookingCreateView(generics.CreateAPIView):
    """Enhanced booking creation with proper validation and payment integration"""
    serializer_class = FlutterBookingCreateSerializer  # Use Flutter-optimized serializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        customer_profile = self.request.user.Customer_profile
        return booking.objects.filter(customer=customer_profile).order_by('-created_at')

    def perform_create(self, serializer):
        # Customer profile is set in the serializer
        booking_instance = serializer.save()
        
        # Auto-calculate and award loyalty points for bookings above KES 2500
        try:
            customer_profile = booking_instance.customer
            booking_amount = float(booking_instance.total_amount)
            
            if booking_amount > 2500:
                points_earned = customer_profile.award_booking_points(
                    booking_amount=booking_amount,
                    booking_id=booking_instance.id
                )
                if points_earned > 0:
                    logger.info(f"Awarded {points_earned} loyalty points to {customer_profile.user.username} for booking {booking_instance.booking_number}")
                    
        except Exception as e:
            logger.error(f"Error calculating loyalty points for booking {booking_instance.id}: {str(e)}")
        
        # Log booking creation
        logger.info(f"Booking created: {booking_instance.booking_number} by {self.request.user.username}")
        
        return booking_instance

    def create(self, request, *args, **kwargs):
        """Override create to handle payment initialization and ensure booking ID is returned"""
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            # Create booking
            booking_instance = self.perform_create(serializer)
            
            # Ensure the booking was created successfully and has a valid ID
            if not booking_instance or not booking_instance.id:
                logger.error("Booking was created but has no valid ID")
                return Response({
                    'success': False,
                    'error': 'Booking creation failed - invalid booking ID',
                    'message': 'Failed to create booking properly'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            response_data = self.get_serializer(booking_instance).data
            
            # Ensure booking_id is explicitly set in response
            response_data['booking_id'] = booking_instance.id
            response_data['id'] = booking_instance.id
            
            # Add loyalty points information to response
            customer_profile = booking_instance.customer
            response_data['loyalty_info'] = {
                'current_points': customer_profile.loyalty_points,
                'loyalty_tier': customer_profile.get_loyalty_tier(),
                'points_earned_this_booking': 0  # Will be updated if points were earned
            }
            
            # Check if loyalty points were earned for this booking
            booking_amount = float(booking_instance.total_amount)
            if booking_amount > 2500:
                points_earned = customer_profile.calculate_booking_loyalty_points(booking_amount)
                response_data['loyalty_info']['points_earned_this_booking'] = points_earned
            
            # Initialize payment if requested
            initialize_payment = request.data.get('initialize_payment', False)
            if initialize_payment and booking_instance.payment_method == 'mpesa':
                payment_result = initiate_mpesa_payment(booking_instance)
                response_data['payment_initialization'] = payment_result
            
            # Flutter-friendly response format
            flutter_response = {
                'success': True,
                'message': 'Booking created successfully',
                'data': response_data
            }
            
            headers = self.get_success_headers(response_data)
            logger.info(f"Booking created successfully: ID={booking_instance.id}, Number={booking_instance.booking_number}")
            
            return Response(flutter_response, status=status.HTTP_201_CREATED, headers=headers)
            
        except Exception as e:
            logger.error(f"Booking creation error: {str(e)}")
            return Response({
                'success': False,
                'error': 'Booking creation failed',
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

class BookingListView(generics.ListAPIView):
    """List bookings for authenticated customer with filtering"""
    serializer_class = BookingDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        customer_profile = self.request.user.Customer_profile
        queryset = booking.objects.filter(customer=customer_profile).order_by('-created_at')
        
        # Apply filters
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        payment_status_filter = self.request.query_params.get('payment_status')
        if payment_status_filter:
            queryset = queryset.filter(payment_status=payment_status_filter)
        
        # Date range filter
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        if date_from:
            queryset = queryset.filter(booking_date__gte=date_from)
        if date_to:
            queryset = queryset.filter(booking_date__lte=date_to)
        
        return queryset

class BookingHistoryView(generics.ListAPIView):
    """Get latest booking history for authenticated customer with comprehensive details"""
    serializer_class = BookingDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        customer_profile = self.request.user.Customer_profile
        # Default to last 50 bookings, ordered by most recent
        queryset = booking.objects.filter(customer=customer_profile).order_by('-created_at')
        
        # Limit parameter for how many recent bookings to show
        limit = self.request.query_params.get('limit', 20)
        try:
            limit = int(limit)
            if limit > 100:  # Max limit to prevent performance issues
                limit = 100
        except ValueError:
            limit = 20
            
        return queryset[:limit]
    
    def list(self, request, *args, **kwargs):
        """Enhanced list response with additional statistics"""
        try:
            queryset = self.get_queryset()
            customer_profile = request.user.Customer_profile
            
            # Get all customer bookings for statistics
            all_bookings = booking.objects.filter(customer=customer_profile)
            
            # Serialize booking data
            serializer = self.get_serializer(queryset, many=True)
            
            # Calculate statistics
            total_bookings = all_bookings.count()
            completed_bookings = all_bookings.filter(status='completed').count()
            cancelled_bookings = all_bookings.filter(status='cancelled').count()
            pending_bookings = all_bookings.filter(status__in=['pending', 'confirmed']).count()
            
            # Calculate total spent
            from django.db.models import Sum
            total_spent = all_bookings.filter(
                payment_status='completed'
            ).aggregate(total=Sum('total_amount'))['total'] or 0
            
            # Recent activity (last 30 days)
            from datetime import datetime, timedelta
            thirty_days_ago = datetime.now() - timedelta(days=30)
            recent_bookings = all_bookings.filter(created_at__gte=thirty_days_ago).count()
            
            # Most used service
            most_used_service = None
            if total_bookings > 0:
                from django.db.models import Count
                service_stats = all_bookings.values(
                    'location_service__service__name'
                ).annotate(
                    count=Count('id')
                ).order_by('-count').first()
                
                if service_stats:
                    most_used_service = {
                        'name': service_stats['location_service__service__name'],
                        'count': service_stats['count']
                    }
            
            response_data = {
                'success': True,
                'message': 'Booking history retrieved successfully',
                'data': {
                    'bookings': serializer.data,
                    'statistics': {
                        'total_bookings': total_bookings,
                        'completed_bookings': completed_bookings,
                        'cancelled_bookings': cancelled_bookings,
                        'pending_bookings': pending_bookings,
                        'total_spent': float(total_spent),
                        'recent_bookings_30_days': recent_bookings,
                        'most_used_service': most_used_service,
                        'loyalty_points': customer_profile.loyalty_points,
                        'loyalty_tier': customer_profile.get_loyalty_tier()
                    },
                    'pagination': {
                        'limit': len(queryset),
                        'total_available': total_bookings,
                        'showing_latest': True
                    }
                }
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error retrieving booking history for {request.user.username}: {str(e)}")
            return Response({
                'success': False,
                'message': 'Error retrieving booking history',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class BookingDetailView(generics.RetrieveAPIView):
    """Get detailed booking information"""
    serializer_class = BookingDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        customer_profile = self.request.user.Customer_profile
        return booking.objects.filter(customer=customer_profile)

class BookingUpdateView(generics.UpdateAPIView):
    """Update booking details (limited fields only)"""
    serializer_class = BookingUpdateSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        customer_profile = self.request.user.Customer_profile
        return booking.objects.filter(customer=customer_profile)

    def perform_update(self, serializer):
        booking = serializer.save()
        logger.info(f"Booking updated: {booking.booking_number} by {self.request.user.username}")

class BookingCancelView(generics.UpdateAPIView):
    """Cancel a booking"""
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        customer_profile = self.request.user.Customer_profile
        return booking.objects.filter(customer=customer_profile)

    def patch(self, request, *args, **kwargs):
        booking = self.get_object()
        
        if not booking.can_be_cancelled():
            return Response({
                'error': 'This booking cannot be cancelled. Please contact support.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Cancel booking
        old_status = booking.status
        booking.status = 'cancelled'
        booking.save()
        
        # Create status history
        BookingStatusHistory.objects.create(
            booking=booking,
            from_status=old_status,
            to_status='cancelled',
            reason=request.data.get('reason', 'Cancelled by customer'),
            changed_by=f"Customer: {request.user.username}"
        )
        
        # Handle refund if payment was made
        if booking.payment_status == 'paid':
            # TODO: Implement refund logic based on payment method
            booking.payment_status = 'refunded'
            booking.save()
        
        logger.info(f"Booking cancelled: {booking.booking_number} by {request.user.username}")
        
        return Response({
            'message': 'Booking cancelled successfully',
            'booking': BookingDetailSerializer(booking).data
        })

class PaymentInitiationView(generics.GenericAPIView):
    """Initiate payment for a booking"""
    serializer_class = PaymentInitiationSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        booking_id = serializer.validated_data['booking_id']
        payment_method = serializer.validated_data['payment_method']
        phone_number = serializer.validated_data.get('phone_number')
        
        try:
            customer_profile = request.user.Customer_profile
            booking_instance = booking.objects.get(id=booking_id, customer=customer_profile)
        except booking_instance.DoesNotExist:
            return Response({
                'error': 'Booking not found or you do not have permission to access it.'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Update payment method and phone number if provided
        booking_instance.payment_method = payment_method
        if phone_number:
            booking_instance.customer_phone = phone_number
        booking_instance.save()

        # Initiate payment based on method
        if payment_method == 'mpesa':
            result = initiate_mpesa_payment(booking_instance)
        elif payment_method == 'paypal':
            result = initiate_paypal_payment(booking_instance)
        elif payment_method == 'visa':
            result = initiate_visa_payment(booking_instance)
        else:
            return Response({
                'error': 'Unsupported payment method'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(result)

def initiate_mpesa_payment(booking):
    """Initiate M-Pesa STK Push payment"""
    try:
        # Initiate STK Push
        result = mpesa_service.initiate_stk_push(
            phone_number=booking.customer_phone,
            amount=booking.total_amount,
            booking_reference=booking.booking_number,
            description=f"Car Wash Service - {booking.location_service.name}"
        )
        
        if result['success']:
            # Update booking with payment reference
            booking.mpesa_checkout_request_id = result['checkout_request_id']
            booking.payment_reference = result['merchant_request_id']
            booking.payment_status = 'processing'
            booking.save()
            
            # Create payment transaction record
            PaymentTransaction.objects.create(
                booking=booking,
                transaction_id=result['checkout_request_id'],
                payment_method='mpesa',
                amount=booking.total_amount,
                status='initiated',
                gateway_reference=result['merchant_request_id'],
                gateway_response=result['raw_response'],
                mpesa_phone_number=booking.customer_phone
            )
            
            logger.info(f"M-Pesa payment initiated for booking {booking.booking_number}")
            
            return {
                'success': True,
                'message': 'Payment request sent to your phone. Please complete the payment.',
                'checkout_request_id': result['checkout_request_id'],
                'customer_message': result.get('customer_message', '')
            }
        else:
            logger.error(f"M-Pesa payment initiation failed for booking {booking.booking_number}: {result}")
            return {
                'success': False,
                'error': result.get('response_description', 'Payment initiation failed'),
                'details': result
            }
            
    except Exception as e:
        logger.error(f"M-Pesa payment error for booking {booking.booking_number}: {str(e)}")
        return {
            'success': False,
            'error': 'Payment service temporarily unavailable. Please try again later.'
        }

def initiate_paypal_payment(booking):
    """Placeholder for PayPal payment initiation"""
    # TODO: Implement PayPal integration
    return {
        'success': False,
        'error': 'PayPal integration not yet implemented'
    }

def initiate_visa_payment(booking):
    """Placeholder for Visa payment initiation"""
    # TODO: Implement Visa/Card payment integration
    return {
        'success': False,
        'error': 'Visa payment integration not yet implemented'
    }

@csrf_exempt
def mpesa_callback(request):
    """Handle M-Pesa payment callback"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        # Parse callback data
        data = json.loads(request.body.decode('utf-8'))
        stk_callback = data.get('Body', {}).get('stkCallback', {})
        
        result_code = stk_callback.get('ResultCode')
        result_desc = stk_callback.get('ResultDesc', '')
        checkout_request_id = stk_callback.get('CheckoutRequestID')
        merchant_request_id = stk_callback.get('MerchantRequestID')
        
        logger.info(f"M-Pesa callback received: {checkout_request_id}, Result: {result_code}")
        
        if not checkout_request_id:
            logger.error("M-Pesa callback missing CheckoutRequestID")
            return JsonResponse({"ResultCode": 1, "ResultDesc": "Invalid callback data"})
        
        # Find the booking
        try:
            booking = booking.objects.get(mpesa_checkout_request_id=checkout_request_id)
        except booking.DoesNotExist:
            logger.error(f"Booking not found for CheckoutRequestID: {checkout_request_id}")
            return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})
        
        # Update payment transaction
        transaction_obj = PaymentTransaction.objects.filter(
            booking=booking,
            transaction_id=checkout_request_id
        ).first()
        
        if result_code == 0:  # Success
            # Extract payment details from callback metadata
            callback_metadata = stk_callback.get('CallbackMetadata', {}).get('Item', [])
            amount = None
            phone_number = None
            transaction_id = None
            
            for item in callback_metadata:
                name = item.get('Name')
                value = item.get('Value')
                
                if name == 'Amount':
                    amount = value
                elif name == 'PhoneNumber':
                    phone_number = value
                elif name == 'MpesaReceiptNumber':
                    transaction_id = value
            
            # Update booking
            booking.payment_status = 'paid'
            booking.status = 'confirmed'
            booking.mpesa_transaction_id = transaction_id
            booking.payment_completed_at = timezone.now()
            booking.save()
            
            # Update transaction record
            if transaction_obj:
                transaction_obj.status = 'successful'
                transaction_obj.completed_at = timezone.now()
                transaction_obj.mpesa_receipt_number = transaction_id
                transaction_obj.mpesa_phone_number = phone_number
                transaction_obj.gateway_response = stk_callback
                transaction_obj.save()
            
            # Create status history
            BookingStatusHistory.objects.create(
                booking=booking,
                from_status='pending',
                to_status='confirmed',
                reason=f'Payment completed via M-Pesa - {transaction_id}',
                changed_by='System'
            )
            
            logger.info(f"Payment successful for booking {booking.booking_number}: KES {amount}, Receipt: {transaction_id}")
            
        else:  # Payment failed
            booking.payment_status = 'failed'
            booking.save()
            
            if transaction_obj:
                transaction_obj.status = 'failed'
                transaction_obj.gateway_response = stk_callback
                transaction_obj.save()
            
            # Create status history
            BookingStatusHistory.objects.create(
                booking=booking,
                from_status='pending',
                to_status='pending',
                reason=f'Payment failed: {result_desc}',
                changed_by='System'
            )
            
            logger.warning(f"Payment failed for booking {booking.booking_number}: {result_desc}")
        
        return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})
        
    except json.JSONDecodeError:
        logger.error("Invalid JSON in M-Pesa callback")
        return JsonResponse({"ResultCode": 1, "ResultDesc": "Invalid JSON"})
    except Exception as e:
        logger.error(f"Error processing M-Pesa callback: {str(e)}")
        return JsonResponse({"ResultCode": 1, "ResultDesc": "Processing error"})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def check_payment_status(request):
    """Check payment status for a booking"""
    booking_id = request.data.get('booking_id')
    
    if not booking_id:
        return Response({'error': 'booking_id is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        customer_profile = request.user.Customer_profile
        booking = booking.objects.get(id=booking_id, customer=customer_profile)
    except booking.DoesNotExist:
        return Response({'error': 'Booking not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # For M-Pesa, query transaction status if needed
    if booking.payment_method == 'mpesa' and booking.mpesa_checkout_request_id and booking.payment_status == 'processing':
        result = mpesa_service.query_transaction_status(booking.mpesa_checkout_request_id)
        
        if result['success']:
            result_code = result.get('result_code')
            if result_code == 0:  # Success
                booking.payment_status = 'paid'
                booking.status = 'confirmed'
                booking.save()
            elif result_code in [1032, 1037]:  # User cancelled or timeout
                booking.payment_status = 'failed'
                booking.save()
    
    return Response({
        'booking_id': booking.id,
        'payment_status': booking.payment_status,
        'booking_status': booking.status,
        'amount': booking.total_amount,
        'payment_method': booking.payment_method
    })

# Tenant-specific views for booking management
class TenantBookingListView(generics.ListAPIView):
    """List all bookings for a tenant's locations"""
    serializer_class = BookingDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Assuming tenant authentication
        tenant = self.request.user  # Adjust based on your tenant auth
        return booking.objects.filter(location__tenant=tenant).order_by('-created_at')

class TenantBookingStatsView(generics.GenericAPIView):
    """Get booking statistics for tenant dashboard"""
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        tenant = request.user  # Adjust based on your tenant auth
        
        # Calculate stats
        total_bookings = booking.objects.filter(location__tenant=tenant).count()
        pending_bookings = booking.objects.filter(location__tenant=tenant, status='pending').count()
        confirmed_bookings = booking.objects.filter(location__tenant=tenant, status='confirmed').count()
        completed_bookings = booking.objects.filter(location__tenant=tenant, status='completed').count()
        cancelled_bookings = booking.objects.filter(location__tenant=tenant, status='cancelled').count()
        
        # Revenue stats
        from django.db.models import Sum
        total_revenue = booking.objects.filter(
            location__tenant=tenant,
            payment_status='paid'
        ).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        
        # Today's bookings
        today = timezone.now().date()
        today_bookings = booking.objects.filter(
            location__tenant=tenant,
            booking_date__date=today
        ).count()
        
        return Response({
            'total_bookings': total_bookings,
            'pending_bookings': pending_bookings,
            'confirmed_bookings': confirmed_bookings,
            'completed_bookings': completed_bookings,
            'cancelled_bookings': cancelled_bookings,
            'total_revenue': total_revenue,
            'today_bookings': today_bookings
        })

class PaymentStatusView(generics.GenericAPIView):
    """Check payment status for a booking"""
    serializer_class = PaymentStatusSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        booking_id = serializer.validated_data['booking_id']
        
        try:
            customer_profile = request.user.Customer_profile
            booking = Booking.objects.get(id=booking_id, customer=customer_profile)
        except Booking.DoesNotExist:
            return Response({
                'error': 'Booking not found or you do not have permission to access it.'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # For M-Pesa, query transaction status if needed
        if (booking.payment_method == 'mpesa' and 
            booking.mpesa_checkout_request_id and 
            booking.payment_status == 'processing'):
            
            result = mpesa_service.query_transaction_status(booking.mpesa_checkout_request_id)
            
            if result['success']:
                result_code = result.get('result_code')
                if result_code == 0:  # Success
                    booking.payment_status = 'paid'
                    booking.status = 'confirmed'
                    booking.save()
                elif result_code in [1032, 1037]:  # User cancelled or timeout
                    booking.payment_status = 'failed'
                    booking.save()
        
        return Response({
            'booking_id': booking.id,
            'payment_status': booking.payment_status,
            'booking_status': booking.status,
            'amount': booking.total_amount,
            'payment_method': booking.payment_method,
            'payment_reference': booking.payment_reference,
            'mpesa_transaction_id': getattr(booking, 'mpesa_transaction_id', None)
        })
        
#api view to handle deletion of bookings
class BookingDeleteView(generics.DestroyAPIView):
    """Delete a booking"""
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        booking_id = self.kwargs.get('pk')
        customer_profile = self.request.user.Customer_profile
        booking_instance = get_object_or_404(booking, id=booking_id, customer=customer_profile)
        return booking_instance

    def perform_destroy(self, instance):
        # Log the deletion
        logger.info(f"Booking deleted: {instance.booking_number} by {self.request.user.username}")
        
        # Delete the booking
        instance.delete()
        
        return Response({'message': 'Booking deleted successfully'}, status=status.HTTP_204_NO_CONTENT)
    
    #modify payment initiations
        # ...existing imports...
    
    from .serializer import (
        BookingCreateSerializer, 
        BookingDetailSerializer, 
        BookingUpdateSerializer,
        FlutterBookingCreateSerializer,
        PaymentInitiationSerializer,
        PaymentInitiationURLSerializer,  # Add this import
        PaymentStatusSerializer,
    )
    
    # ...existing code...
    
    class PaymentInitiationView(generics.GenericAPIView):
        """Initiate payment for a booking using booking_id from URL"""
        serializer_class = PaymentInitiationURLSerializer
        permission_classes = [IsAuthenticated]
        lookup_field = 'pk'
    
        def get_object(self):
            """Get the booking object from URL parameter"""
            booking_id = self.kwargs.get('pk')
            try:
                customer_profile = self.request.user.Customer_profile
                return booking.objects.get(id=booking_id, customer=customer_profile)
            except booking.DoesNotExist:
                return None
    
        def post(self, request, pk):
            """Initiate payment for a specific booking"""
            # Get the booking from URL parameter
            booking_instance = self.get_object()
            
            if not booking_instance:
                return Response({
                    'success': False,
                    'error': 'Booking not found or you do not have permission to access it.',
                    'message': 'Invalid booking ID or unauthorized access'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Validate the request data (payment_method, phone_number)
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            payment_method = serializer.validated_data['payment_method']
            phone_number = serializer.validated_data.get('phone_number')
            
            # Check if booking can accept payment
            if booking_instance.payment_status == 'paid':
                return Response({
                    'success': False,
                    'error': 'Payment already completed for this booking',
                    'message': 'This booking has already been paid for'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if booking_instance.status == 'cancelled':
                return Response({
                    'success': False,
                    'error': 'Cannot process payment for cancelled booking',
                    'message': 'This booking has been cancelled'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Update payment method and phone number if provided
            booking_instance.payment_method = payment_method
            if phone_number:
                booking_instance.customer_phone = phone_number
            booking_instance.save()
    
            # Initiate payment based on method
            try:
                if payment_method == 'mpesa':
                    result = initiate_mpesa_payment(booking_instance)
                elif payment_method == 'paypal':
                    result = initiate_paypal_payment(booking_instance)
                elif payment_method == 'visa':
                    result = initiate_visa_payment(booking_instance)
                else:
                    return Response({
                        'success': False,
                        'error': 'Unsupported payment method',
                        'message': f'Payment method {payment_method} is not supported'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Add booking information to the result
                result['booking_id'] = booking_instance.id
                result['booking_number'] = booking_instance.booking_number
                result['amount'] = str(booking_instance.total_amount)
                
                return Response(result)
                
            except Exception as e:
                logger.error(f"Payment initiation error for booking {booking_instance.id}: {str(e)}")
                return Response({
                    'success': False,
                    'error': 'Payment initiation failed',
                    'message': 'Unable to process payment request. Please try again.'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    # Keep the old view for backward compatibility
    class PaymentInitiationLegacyView(generics.GenericAPIView):
        """Legacy payment initiation view (booking_id in request body)"""
        serializer_class = PaymentInitiationSerializer
        permission_classes = [IsAuthenticated]
    
        def post(self, request):
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            booking_id = serializer.validated_data['booking_id']
            payment_method = serializer.validated_data['payment_method']
            phone_number = serializer.validated_data.get('phone_number')
            
            try:
                customer_profile = request.user.Customer_profile
                booking_instance = booking.objects.get(id=booking_id, customer=customer_profile)
            except booking.DoesNotExist:
                return Response({
                    'error': 'Booking not found or you do not have permission to access it.'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Update payment method and phone number if provided
            booking_instance.payment_method = payment_method
            if phone_number:
                booking_instance.customer_phone = phone_number
            booking_instance.save()
    
            # Initiate payment based on method
            if payment_method == 'mpesa':
                result = initiate_mpesa_payment(booking_instance)
            elif payment_method == 'paypal':
                result = initiate_paypal_payment(booking_instance)
            elif payment_method == 'visa':
                result = initiate_visa_payment(booking_instance)
            else:
                return Response({
                    'error': 'Unsupported payment method'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            return Response(result)
    
    