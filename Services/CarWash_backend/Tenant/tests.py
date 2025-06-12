from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APIRequestFactory, force_authenticate, APITestCase
from Tenant.models import Tenant, TenantProfile, Employee
from django.contrib.auth import get_user_model
from Tenant.views import DeleteEmployeeView




# #test case for employee deletion
class EmployeeDeletionTestCase(APITestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Test Tenant",
            contact_email="workjhccd",
            contact_phone="1234567890",
            password="testpassword"
        )
        self.tenant_profile = TenantProfile.objects.create(
            tenant=self.tenant,
            username="test_tenant",
            business_name="Test Business",
            business_email=" "
        )
        self.employee = self.tenant.employees.create(
            username="test_employee",
            email="test_employee@example.com"
        )
        self.url = reverse('delete_employee', kwargs={'pk': self.employee.pk})
        self.client = APIClient()

    def test_delete_employee(self):
        self.client.force_authenticate(user=self.tenant_profile)
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(Employee.objects.filter(pk=self.employee.pk).exists())
        self.assertEqual(Employee.objects.filter(tenant=self.tenant).count(), 0)
        self.assertEqual(self.tenant.employees.count(), 0)

 