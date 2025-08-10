from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal
from datetime import datetime, timedelta


#creating cutomer profile model
class CustomerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='Customer_profile')
    first_name = models.CharField(max_length=30, blank=True, null=True)
    last_name = models.CharField(max_length=30, blank=True, null=True)
    email = models.EmailField(max_length=254, blank=True, null=True)
    
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    loyalty_points = models.PositiveIntegerField(default=0)
    last_login_points_awarded = models.DateTimeField(null=True, blank=True)
    total_spent = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total_bookings = models.PositiveIntegerField(default=0)
    updated_at= models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    
    # Loyalty points configuration
    BOOKING_POINTS_THRESHOLD = Decimal('2500.00')  # Minimum amount for booking points
    BOOKING_POINTS_RATE = 0.02  # 2% of booking amount as points (2500 = 50 points)
    LOGIN_POINTS = 5  # Points awarded per login
    LOGIN_POINTS_COOLDOWN_HOURS = 24  # Hours between login point awards

    def calculate_booking_loyalty_points(self, booking_amount):
        """
        Calculate loyalty points based on booking amount.
        Awards 2% of booking amount as points if amount >= 2500
        """
        booking_amount = Decimal(str(booking_amount))
        
        if booking_amount >= self.BOOKING_POINTS_THRESHOLD:
            points = int(booking_amount * Decimal(str(self.BOOKING_POINTS_RATE)))
            return points
        return 0
    
    def award_booking_points(self, booking_amount, booking_id=None):
        """
        Award loyalty points for a booking and log the transaction.
        """
        points_earned = self.calculate_booking_loyalty_points(booking_amount)
        
        if points_earned > 0:
            self.loyalty_points += points_earned
            self.total_spent += Decimal(str(booking_amount))
            self.total_bookings += 1
            self.save()
            
            # Log the loyalty points transaction
            LoyaltyPointsTransaction.objects.create(
                customer=self,
                transaction_type='booking',
                points_earned=points_earned,
                booking_amount=booking_amount,
                booking_id=booking_id,
                description=f"Booking reward: {points_earned} points for ₹{booking_amount} booking"
            )
            
            return points_earned
        return 0
    
    def can_award_login_points(self):
        """
        Check if user can receive login points (24-hour cooldown).
        """
        if not self.last_login_points_awarded:
            return True
        
        cooldown_time = self.last_login_points_awarded + timedelta(hours=self.LOGIN_POINTS_COOLDOWN_HOURS)
        return timezone.now() > cooldown_time
    
    def award_login_points(self):
        """
        Award login points if eligible (once per 24 hours).
        """
        if self.can_award_login_points():
            self.loyalty_points += self.LOGIN_POINTS
            self.last_login_points_awarded = timezone.now()
            self.save()
            
            # Log the loyalty points transaction
            LoyaltyPointsTransaction.objects.create(
                customer=self,
                transaction_type='login',
                points_earned=self.LOGIN_POINTS,
                description=f"Daily login bonus: {self.LOGIN_POINTS} points"
            )
            
            return self.LOGIN_POINTS
        return 0
    
    def redeem_points(self, points_to_redeem, reason="Points redemption"):
        """
        Redeem loyalty points (subtract from total).
        """
        if points_to_redeem <= self.loyalty_points:
            self.loyalty_points -= points_to_redeem
            self.save()
            
            # Log the redemption
            LoyaltyPointsTransaction.objects.create(
                customer=self,
                transaction_type='redemption',
                points_earned=-points_to_redeem,
                description=f"Points redeemed: {points_to_redeem} points - {reason}"
            )
            
            return True
        return False
    
    def get_loyalty_tier(self):
        """
        Determine customer loyalty tier based on total spent.
        """
        if self.total_spent >= 50000:
            return "Platinum"
        elif self.total_spent >= 25000:
            return "Gold"
        elif self.total_spent >= 10000:
            return "Silver"
        else:
            return "Bronze"
    
    def get_points_to_next_tier(self):
        """
        Calculate points needed to reach next loyalty tier.
        """
        current_tier = self.get_loyalty_tier()
        tier_thresholds = {
            "Bronze": 10000,
            "Silver": 25000,
            "Gold": 50000,
            "Platinum": None
        }
        
        if current_tier == "Platinum":
            return 0
        
        next_threshold = tier_thresholds[current_tier]
        return float(next_threshold - self.total_spent)

    def __str__(self):
        return f"{self.user.username}'s Profile ({self.loyalty_points} points)"
    
    class Meta:
        verbose_name = 'Customer Profile'
        verbose_name_plural = 'Customer Profiles'


class LoyaltyPointsTransaction(models.Model):
    """
    Model to track all loyalty points transactions (earned, redeemed, etc.)
    """
    TRANSACTION_TYPES = [
        ('booking', 'Booking Reward'),
        ('login', 'Login Bonus'),
        ('redemption', 'Points Redemption'),
        ('bonus', 'Special Bonus'),
        ('refund', 'Booking Refund'),
        ('adjustment', 'Manual Adjustment'),
    ]
    
    customer = models.ForeignKey(CustomerProfile, on_delete=models.CASCADE, related_name='loyalty_transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    points_earned = models.IntegerField()  # Can be negative for redemptions
    booking_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    booking_id = models.PositiveIntegerField(null=True, blank=True)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        action = "earned" if self.points_earned > 0 else "redeemed"
        return f"{self.customer.user.username} {action} {abs(self.points_earned)} points - {self.transaction_type}"
    
    class Meta:
        verbose_name = 'Loyalty Points Transaction'
        verbose_name_plural = 'Loyalty Points Transactions'
        ordering = ['-created_at']
        
        
        
        # this model is used to store user audit logs
class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('register', 'register user'),
        ('login', 'login user'),
        ('logout', 'logout user'),
        ('login_failed', 'login failed'),
        ('update_profile', 'update profile'),
        ('delete_account', 'delete account'),
        ('reset_password', 'reset password'),
        ('change_password', 'change password'),
        
        ('other', 'other'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='audit_logs')
    action = models.CharField(choices=ACTION_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.JSONField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.CharField(max_length=255, blank=True, null=True)
    success = models.BooleanField(default=False)  # Default to False, set True on success

    def __str__(self):
        if self.user and self.user.username:
            username = self.user.username
        else:
            username = 'Anonymous'
        return f"{username} - {self.action} at {self.timestamp} (Success: {self.success})"

    class Meta:
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'
        ordering = ['-timestamp']
        
        

class Favorite(models.Model):
    
    #Model representing a user's favorite location.

    user = models.ForeignKey('CustomerProfile', on_delete=models.CASCADE, related_name='favorites')
    location = models.ForeignKey('Location.Location', on_delete=models.CASCADE, related_name='favorited_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'location')