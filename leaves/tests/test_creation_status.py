from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from django.urls import reverse
from rest_framework.test import APIClient

from users.models import CustomUser, Department, Affiliate
from leaves.models import LeaveType, LeaveRequest


class CreationStatusEscalationTests(TestCase):
    def setUp(self):
        # Affiliates
        self.aff_merban = Affiliate.objects.create(name="Merban Capital")
        self.aff_sdsl = Affiliate.objects.create(name="SDSL")
        self.aff_sbl = Affiliate.objects.create(name="SBL")

        # Departments
        self.dept_it = Department.objects.create(name="IT", affiliate=self.aff_merban)
        self.dept_orphans = Department.objects.create(name="Orphans", affiliate=self.aff_merban)

        # Users
        self.manager_merban = CustomUser.objects.create_user(
            username="mer_manager",
            password="x",
            employee_id="MGR001",
            role="manager",
            department=self.dept_it,
            affiliate=self.aff_merban,
        )
        # Set manager as HOD of IT
        self.dept_it.hod = self.manager_merban
        self.dept_it.save(update_fields=["hod"])

        self.hr_merban = CustomUser.objects.create_user(
            username="mer_hr",
            password="x",
            employee_id="HR001",
            role="hr",
            department=self.dept_it,
            affiliate=self.aff_merban,
        )
        self.hr_sdsl = CustomUser.objects.create_user(
            username="sdsl_hr",
            password="x",
            employee_id="HR002",
            role="hr",
            affiliate=self.aff_sdsl,
        )
        self.staff_with_manager = CustomUser.objects.create_user(
            username="mer_staff_mgr",
            password="x",
            employee_id="STF001",
            role="junior_staff",
            department=self.dept_it,
            affiliate=self.aff_merban,
            manager=self.manager_merban,
        )
        self.staff_no_mgr_no_hod = CustomUser.objects.create_user(
            username="mer_staff_orphan",
            password="x",
            employee_id="STF002",
            role="junior_staff",
            department=self.dept_orphans,  # no HOD assigned
            affiliate=self.aff_merban,
        )

        # Leave type
        self.annual = LeaveType.objects.create(name="Annual")

        self.client = APIClient()
        self.url = reverse("leave-requests-list")
        self.tomorrow = (timezone.now() + timedelta(days=1)).date()
        self.day_after = (timezone.now() + timedelta(days=2)).date()

    def _post_request(self, user):
        self.client.force_authenticate(user=user)
        payload = {
            "leave_type": self.annual.id,
            "start_date": self.tomorrow,
            "end_date": self.day_after,
            "reason": "testing",
        }
        resp = self.client.post(self.url, data=payload, format="json")
        # Must succeed
        self.assertIn(resp.status_code, (200, 201), resp.content)
        # Get created object
        obj = LeaveRequest.objects.filter(employee=user).order_by("-id").first()
        self.assertIsNotNone(obj)
        return obj

    def test_manager_request_escalates_to_manager_approved(self):
        obj = self._post_request(self.manager_merban)
        self.assertEqual(obj.status, "manager_approved")

    def test_hr_merban_request_escalates_to_manager_approved(self):
        obj = self._post_request(self.hr_merban)
        self.assertEqual(obj.status, "manager_approved")

    def test_hr_sdsl_request_escalates_to_ceo_approved(self):
        obj = self._post_request(self.hr_sdsl)
        self.assertEqual(obj.status, "ceo_approved")

    def test_staff_with_manager_or_hod_starts_pending(self):
        obj = self._post_request(self.staff_with_manager)
        self.assertEqual(obj.status, "pending")

    def test_staff_no_manager_no_hod_merban_escalates_to_manager_approved(self):
        obj = self._post_request(self.staff_no_mgr_no_hod)
        self.assertEqual(obj.status, "manager_approved")
