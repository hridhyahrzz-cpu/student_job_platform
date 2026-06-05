from django.test import TestCase, Client
from users_app.models import UserModel
from jobs_app.models import JobModel, ApplicationModel

class UpdateApplicationStatusAJAXTest(TestCase):
    def setUp(self):
        self.client = Client()
        
        # Create recruiter who owns the job
        self.recruiter = UserModel.objects.create_user(username="recruiter1", password="password", user_type="recruiter")
        
        # Create another recruiter
        self.other_recruiter = UserModel.objects.create_user(username="recruiter2", password="password", user_type="recruiter")
        
        # Create student applicant
        self.student = UserModel.objects.create_user(username="student1", password="password", user_type="student")
        
        # Create job
        self.job = JobModel.objects.create(
            title="Software Intern",
            description="Django intern job.",
            company_name="TechInc",
            location="Remote",
            salary=50000,
            created_by=self.recruiter
        )
        
        # Create application
        self.application = ApplicationModel.objects.create(
            job=self.job,
            applicant=self.student,
            cover_letter="Interested in this job."
        )

    def test_ajax_update_status_accepted(self):
        self.client.login(username="recruiter1", password="password")
        
        response = self.client.post(
            f"/applications/{self.application.id}/status/",
            data='{"status": "accepted"}',
            content_type="application/json",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        
        self.assertEqual(response.status_code, 200)
        json_data = response.json()
        self.assertTrue(json_data["success"])
        self.assertEqual(json_data["status"], "accepted")
        
        # Check database
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, "accepted")

    def test_ajax_update_status_rejected(self):
        self.client.login(username="recruiter1", password="password")
        
        response = self.client.post(
            f"/applications/{self.application.id}/status/",
            data='{"status": "rejected"}',
            content_type="application/json",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        
        self.assertEqual(response.status_code, 200)
        json_data = response.json()
        self.assertTrue(json_data["success"])
        self.assertEqual(json_data["status"], "rejected")
        
        # Check database
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, "rejected")

    def test_ajax_update_status_invalid_value(self):
        self.client.login(username="recruiter1", password="password")
        
        response = self.client.post(
            f"/applications/{self.application.id}/status/",
            data='{"status": "invalid_status_value"}',
            content_type="application/json",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        
        self.assertEqual(response.status_code, 400)
        json_data = response.json()
        self.assertFalse(json_data["success"])
        
        # Database status should remain pending
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, "pending")

    def test_ajax_update_status_by_student_forbidden(self):
        self.client.login(username="student1", password="password")
        
        response = self.client.post(
            f"/applications/{self.application.id}/status/",
            data='{"status": "accepted"}',
            content_type="application/json",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        
        self.assertEqual(response.status_code, 403)

    def test_ajax_update_status_by_other_recruiter_forbidden(self):
        self.client.login(username="recruiter2", password="password")
        
        response = self.client.post(
            f"/applications/{self.application.id}/status/",
            data='{"status": "accepted"}',
            content_type="application/json",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        
        self.assertEqual(response.status_code, 403)
