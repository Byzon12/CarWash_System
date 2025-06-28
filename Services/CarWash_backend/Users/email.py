from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import EmailMessage
from django.core.mail import send_mail
import requests
from user_agents import parse

#function to get the client's IP address from the request
def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

# Function to get the user's device information from the request
def get_user_device_info(request):
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    parsed = parse(user_agent)
    return {
        'browser': parsed.browser.family,
        'os': parsed.os.family,
        'device': parsed.device.family
    }
# function to get user's location based on IP address
def get_user_location(ip_address):
    try:
        response = requests.get(f"http://ip-api.com/json/{ip_address}")
        data = response.json()
        if data['status'] == 'success':
            return {
                'country': data.get('country', ''),
                'region': data.get('regionName', ''),
                'city': data.get('city', ''),
                'zip': data.get('zip', ''),
                'lat': data.get('lat', ''),
                'lon': data.get('lon', '')
            }
        else:
            return {} 
        return response.json()
    except requests.RequestException:
        return {}

def send_email(subject, message, recipient_list):
    from_email = settings.DEFAULT_FROM_EMAIL
    send_mail(subject, message, from_email, recipient_list)

# Email notification for user registration
def send_registration_email(user):
    subject = "Welcome to CarWash"
    message = f"Hi {user.first_name},\n\nThank you for registering at CarWash. We're excited to have you on board!"
    recipient_list = [user.email]
    send_email(subject, message, recipient_list)
# Email notification for password reset
def send_password_reset_email(user, token):
    subject = "Password Reset Request"
    message = f"Hi {user.first_name},\n\nYou requested a password reset. Click the link below to reset your password:\n\n{token}"
    recipient_list = [user.email]
    send_email(subject, message, recipient_list)

def send_login_notification_email(user, request):
    ip_address = get_client_ip(request)
    location = get_user_location(ip_address)
    device_info = get_user_device_info(request)
    user_agent = parse(request.META.get('HTTP_USER_AGENT', ''))

    browser = f"{user_agent.browser.family} {user_agent.browser.version_string}"
    device = "Mobile" if user_agent.is_mobile else "Tablet" if user_agent.is_tablet else "PC"
    os = f"{user_agent.os.family} {user_agent.os.version_string}"

    subject = "Login Notification"
    message = (
        f"Hi {user.first_name},\n\n"
        f"You have successfully logged in to your CarWash account.\n\n"
        f"Login Details:\n"
        f"IP Address: {ip_address}\n"
        f"Location: {location}\n"
        f"Device: {device}\n"
        f"Operating System: {os}\n"
        f"Browser: {browser}\n\n"
        f"If this wasn't you, please reset your password immediately or contact support."
    )
    recipient_list = [user.email]
    send_email(subject, message, recipient_list)
def send_logout_notification_email(user, request):
    ip_address = get_client_ip(request)
    device_info = get_user_device_info(request)
    location = get_user_location(ip_address)

    subject = "Logout Notification"
    message = f"Hi {user.first_name},\n\nYou have successfully logged out of your CarWash account."
    message += f"\n\nLogout Details:"
    message += f"\nIP Address: {ip_address}"
    message += f"\nDevice: {device_info['device']}"
    message += f"\nLocation: {location.get('city', '')}, {location.get('region', '')}, {location.get('country', '')}"
    recipient_list = [user.email]
    send_email(subject, message, recipient_list)


#function to send password reset email
def send_password_reset_email(user, token, uid, request):
    domain = request.get_host() if request else '127.0.0.1:8000'
    protocol = 'https' if request and request.is_secure() else 'http'
    reset_link = f"{protocol}://{domain}/reset-password-confirm/{uid}/{token}/"

    # Email content
    subject = "Password Reset Requested"
    message = f"Hi {user.get_full_name() if hasattr(user, 'get_full_name') else 'User'},\n\n" \
              f"You requested a password reset. Click the link below to reset your password:\n\n{reset_link}\n\n" \
              "If you did not request this, please ignore this email."
    recipient_list = [user.email]

    send_email(subject, message, recipient_list)
    