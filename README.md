# CarWash System Backend API Documentation

This document provides a comprehensive overview of all available API endpoints for the CarWash System backend, organized by module and including the root path for each. Place this file at the project root (e.g., `CarWash_System/README.md`).

---

## Project Root Path
The main API root is:
```
/ (project root)
```
Main URL configuration: `CarWash_System/Services/CarWash_backend/CarWash_backend/urls.py`

---

## Table of Contents
- [Users Module](/user/)
- [Tenant Module](/tenant/)
- [Location Module](/location/)
- [Booking Module](/booking/)
- [Staff Module](/staff/)
- [Report_Analysis Module](/report/)
- [General Notes](#general-notes)

---

## Users Module (`/user/`)
- `register/` (POST): Register user
- `login/` (POST): Login user
- `password-reset/` (POST): Request password reset
- `password-reset-confirm/` (POST): Confirm password reset
- `password-reset-change/` (POST): Change password
- `profile/` (GET/PUT): Get or update user profile
- `logout/` (POST): Logout user
- `flutter/register/`, `flutter/login/`, `flutter/logout/`, `flutter/profile/`, `flutter/status/`, `flutter/check-username/`, `flutter/check-email/`: Flutter-specific endpoints
- `token/`, `token/refresh/`: JWT token endpoints
- `locations/`: List available locations for user
- `locations/services/`: List all location services
- `locations/<int:location_id>/services/`: List services for a specific location
- `loyalty/dashboard/`, `loyalty/history/`, `loyalty/redeem/`, `loyalty/tier-info/`: Loyalty points endpoints
- `favorites/add/` (POST): Add favorite location
- `favorites/remove/` (DELETE): Remove favorite location
- `favorites/` (GET): List favorites

## Tenant Module (`/tenant/`)
- `login/`, `logout/`: Tenant authentication
- `profile/`, `profile/details/`: Tenant profile management
- `employees/list/`, `employees/create/`, `employees/update/<int:pk>/`, `employees/delete/<int:pk>/`, `employees/deactivate/<int:pk>/`, `employees/activate/<int:pk>/`: Employee management
- `roles/create/`, `roles/`: Employee role management
- `tasks/create/`, `tasks/`, `tasks/<int:pk>/`, `tasks/<int:pk>/status/`: Task management
- `tasks/<int:task_id>/checkins/`, `tasks/<int:task_id>/summary/`, `checkins/<int:pk>/checkout/`: Car check-in/out
- `dashboard/stats/`, `staff/statistics/`: Dashboard and statistics

## Location Module (`/location/`)
- `create/`, `update/<int:pk>/`, `delete/<int:pk>/`, `activate/<int:pk>/`, `list/`: Location CRUD
- `services/create/`, `services/list/`, `services/update/<int:pk>/`, `services/delete/<int:pk>/`: Service CRUD
- `location-services/create/`, `location-services/delete/<int:pk>/`, `location-services/list/`, `location-services/detail/<int:pk>/`: Location service management

## Booking Module (`/booking/`)
- `create/` (POST): Create booking
- `list/` (GET): List bookings
- `history/` (GET): Booking history
- `<int:pk>/` (GET): Booking detail
- `<int:pk>/update/` (PUT): Update booking
- `<int:pk>/cancel/` (POST): Cancel booking
- `delete/<int:pk>/` (DELETE): Delete booking
- `payment/initiate/`, `payment/status/`, `<int:pk>/payment/initiate/`: Payment endpoints
- `mpesa-callback/`: Payment callback
- `tenant/list/`, `tenant/stats/`: Tenant booking management

## Staff Module (`/staff/`)
- `login/`, `logout/`, `password-reset/`: Staff authentication
- `profile/`: Staff profile
- `task-statistics/`: Task statistics
- `tasks/`, `tasks/update-status/<int:pk>/`: Task management
- `walkin-customers/`, `walkin-customers/create/`, `walkin-customers/<int:pk>/update/`: Walk-in customer management
- `walkin-tasks/`, `walkin-tasks/<int:pk>/`, `walkin-tasks/<int:pk>/update/`, `walkin-tasks/<int:pk>/status/`, `walkin-tasks/bulk-update/`, `walkin-tasks/templates/`: Walk-in task management
- `walkin-payments/`, `walkin-payments/initiate-mpesa/`, `walkin-payments/<int:payment_id>/status/`: Walk-in payment management
- `walkin-customers/mpesa-callback/`: M-Pesa callback

## Report_Analysis Module (`/report/`)
- `dashboard/`: Analytics dashboard
- `financial-report/`: Financial report
- `operational-report/`: Operational report

---

## General Notes
- All endpoints requiring authentication expect a valid token in the `Authorization` header.
- Data is generally exchanged in JSON format.
- For detailed request/response examples, see the API documentation or use tools like Postman with the provided collection.

---

## Setup & Deployment

1. **Clone the repository**
2. **Install dependencies:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
3. **Configure environment variables and settings in `settings.py`**
4. **Apply migrations:**
   ```bash
   python manage.py migrate
   ```
5. **Create a superuser:**
   ```bash
   python manage.py createsuperuser
   ```
6. **Run the development server:**
   ```bash
   python manage.py runserver
   ```
7. **For production:**
   - Use Gunicorn and Nginx (see deployment instructions above)
   - Set `DEBUG = False` and configure `ALLOWED_HOSTS`
   - Collect static files: `python manage.py collectstatic`

---

## License
This project is licensed under the MIT License.

---

## Contact
For support or inquiries, contact the project maintainer.
byzoneochieng@gmail.com
0700764847/0758898113
