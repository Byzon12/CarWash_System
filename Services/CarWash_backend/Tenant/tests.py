from django.test import TestCase
from django.urls import reverse
from Tenant.models import Tenant, TenantProfile

class TenantModelTests(TestCase):

    def setUp(self):
        self.tenant = Tenant.objects.create(name="Test Tenant")
        self.profile = TenantProfile.objects.create(tenant=self.tenant, address="123 Test St")

    def test_tenant_creation(self):
        self.assertEqual(self.tenant.name, "Test Tenant")

    def test_tenant_profile_creation(self):
        self.assertEqual(self.profile.tenant, self.tenant)
        self.assertEqual(self.profile.address, "123 Test St")


# Create your tests here.
