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

    def test_ajax_update_status_offered(self):
        self.client.login(username="recruiter1", password="password")
        
        response = self.client.post(
            f"/applications/{self.application.id}/status/",
            data='{"status": "offered"}',
            content_type="application/json",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        
        self.assertEqual(response.status_code, 200)
        json_data = response.json()
        self.assertTrue(json_data["success"])
        self.assertEqual(json_data["status"], "offered")
        
        # Check database
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, "offered")

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
        
        # Database status should remain applied
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, "applied")

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
            data='{"status": "offered"}',
            content_type="application/json",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        
        self.assertEqual(response.status_code, 403)

    def test_ajax_update_status_assessment(self):
        self.client.login(username="recruiter1", password="password")
        response = self.client.post(
            f"/applications/{self.application.id}/status/",
            data='{"status": "assessment"}',
            content_type="application/json",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "assessment")
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, "assessment")

    def test_ajax_update_status_technical(self):
        self.client.login(username="recruiter1", password="password")
        response = self.client.post(
            f"/applications/{self.application.id}/status/",
            data='{"status": "technical"}',
            content_type="application/json",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "technical")
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, "technical")


from unittest.mock import patch, MagicMock

class ProfileBackgroundResumeTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = UserModel.objects.create_user(username="student1", password="password", user_type="student")
        
    @patch("threading.Thread")
    def test_profile_save_spawns_thread(self, mock_thread):
        self.client.login(username="student1", password="password")
        
        # Pre-set some old data to verify it gets cleared
        from users_app.models import Profile
        profile, _ = Profile.objects.get_or_create(user=self.user)
        profile.resume_text = "Old resume text"
        profile.score = 50
        profile.save()
        
        # Prepare mock file
        from django.core.files.uploadedfile import SimpleUploadedFile
        resume_file = SimpleUploadedFile("resume.pdf", b"Hello resume text", content_type="application/pdf")
        
        response = self.client.post("/profile/", {
            "full_name": "Student Name",
            "phone_number": "12345",
            "email": "student@example.com",
            "bio": "Some bio",
            "resume": resume_file
        })
        
        self.assertEqual(response.status_code, 200)
        
        # Verify thread was instantiated and started
        self.assertTrue(mock_thread.called)
        inst = mock_thread.return_value
        self.assertTrue(inst.start.called)
        self.assertEqual(mock_thread.call_args[1]["target"].__name__, "handle_background_resume")
        
        # Verify old resume text and score were cleared immediately
        profile.refresh_from_db()
        self.assertEqual(profile.resume_text, "")
        self.assertEqual(profile.score, 0)
        
    @patch("jobs_app.services.resume_scoring.analyze_resume")
    def test_handle_background_resume_worker_runs_successfully(self, mock_analyze):
        mock_analyze.return_value = '{"score": 85, "feedback": "Excellent resume"}'
        
        # Create a profile with a file
        from users_app.models import Profile
        profile, _ = Profile.objects.get_or_create(user=self.user)
        from django.core.files.uploadedfile import SimpleUploadedFile
        profile.resume = SimpleUploadedFile("resume.txt", b"Extracted raw plain text", content_type="text/plain")
        profile.save()
        
        from users_app.views import handle_background_resume
        handle_background_resume(profile.id)
        
        # Verify database was updated
        profile.refresh_from_db()
        self.assertEqual(profile.resume_text, "Extracted raw plain text")
        self.assertEqual(profile.score, 85)
        
        # Verify baseline analyze_resume was triggered
        self.assertTrue(mock_analyze.called)
        self.assertIn("Extracted raw plain text", mock_analyze.call_args[0][0])


class NotificationSystemTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.recruiter = UserModel.objects.create_user(username="recruiter1", password="password", user_type="recruiter")
        self.student = UserModel.objects.create_user(username="student1", password="password", user_type="student")
        
        self.job = JobModel.objects.create(
            title="Python Developer",
            description="Python skills required.",
            company_name="TechInc",
            location="Remote",
            salary=60000,
            created_by=self.recruiter
        )
        
        self.application = ApplicationModel.objects.create(
            job=self.job,
            applicant=self.student,
            cover_letter="I am interested."
        )

    def test_status_update_creates_notification(self):
        self.client.login(username="recruiter1", password="password")
        response = self.client.post(
            f"/applications/{self.application.id}/status/",
            data='{"status": "assessment"}',
            content_type="application/json",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(response.status_code, 200)
        
        from jobs_app.models import NotificationModel
        notifications = NotificationModel.objects.filter(recipient=self.student)
        self.assertEqual(notifications.count(), 1)
        notif = notifications.first()
        self.assertIn("Online Assessment", notif.title)
        self.assertIn("Online Assessment", notif.message)
        self.assertFalse(notif.is_read)

    def test_interview_scheduling_creates_notification(self):
        self.client.login(username="recruiter1", password="password")
        response = self.client.post(
            f"/applications/{self.application.id}/schedule/",
            data={
                "scheduled_time": "2026-06-20T11:00",
                "meeting_link": "https://meet.google.com/abc-defg-hij",
                "notes": "Be ready."
            }
        )
        self.assertEqual(response.status_code, 302) # redirect to dashboard
        
        from jobs_app.models import NotificationModel
        notifications = NotificationModel.objects.filter(recipient=self.student)
        self.assertEqual(notifications.count(), 1)
        notif = notifications.first()
        self.assertIn("Interview Scheduled", notif.title)
        self.assertFalse(notif.is_read)

    def test_mark_notification_read(self):
        from jobs_app.models import NotificationModel
        notif = NotificationModel.objects.create(
            recipient=self.student,
            title="Test Notification",
            message="Hello student"
        )
        self.client.login(username="student1", password="password")
        
        # Test AJAX endpoint
        response = self.client.post(
            f"/notifications/{notif.id}/read/",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        
        notif.refresh_from_db()
        self.assertTrue(notif.is_read)

    def test_dashboard_context_has_notifications(self):
        from jobs_app.models import NotificationModel
        NotificationModel.objects.create(
            recipient=self.student,
            title="Alert 1",
            message="Msg 1"
        )
        
        self.client.login(username="student1", password="password")
        response = self.client.get("/dashboard/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("unread_notifications", response.context)
        self.assertEqual(response.context["unread_notifications"].count(), 1)

