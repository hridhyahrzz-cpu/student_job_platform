from unittest.mock import patch
from django.test import TestCase, Client
from django.core.files.uploadedfile import SimpleUploadedFile
from users_app.models import UserModel, Profile
from jobs_app.models import JobModel, ApplicationModel, QuizModel, QuestionModel, QuizAttemptModel

class ApplyJobPageTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = UserModel.objects.create_user(username="student1", password="password", user_type="student")
        self.profile, _ = Profile.objects.get_or_create(user=self.user)
        
        # Recruiter to create the job
        self.recruiter = UserModel.objects.create_user(username="recruiter1", password="password", user_type="recruiter")
        self.job = JobModel.objects.create(
            title="Python Developer",
            description="Looking for Python developer.",
            company_name="TechCorp",
            location="Remote",
            salary=80000,
            minimum_score=50,
            created_by=self.recruiter
        )
        
        # Give the profile a default plain text resume so that applying works out of the box
        self.profile.resume = SimpleUploadedFile("resume.txt", b"dummy resume content", content_type="text/plain")
        self.profile.save()

    def test_get_apply_page(self):
        self.client.login(username="student1", password="password")
        response = self.client.get(f"/jobs/{self.job.id}/apply/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "jobs_app/apply_job.html")

    def test_apply_without_resume(self):
        # Remove the resume from the profile to trigger the validation error
        self.profile.resume = None
        self.profile.save()
        
        self.client.login(username="student1", password="password")
        response = self.client.post(f"/jobs/{self.job.id}/apply/", {
            "cover_letter": "I love Django."
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "You must upload a resume to your profile first before applying to jobs. Please visit your Profile page.")

    @patch("jobs_app.views.analyze_resume")
    def test_apply_with_low_score(self, mock_analyze):
        mock_analyze.return_value = '{"score": 30, "feedback": "Good try."}'
        self.client.login(username="student1", password="password")
        
        response = self.client.post(f"/jobs/{self.job.id}/apply/", {
            "cover_letter": "I love Django."
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "jobs_app/application_result.html")
        self.assertContains(response, "Application Submitted")
        self.assertContains(response, "You are currently NOT ELIGIBLE for this job.")
        self.assertContains(response, "30 / 100")
        self.assertContains(response, "50 / 100")
        
        # Profile score should still be updated
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.score, 30)

    @patch("jobs_app.views.analyze_resume")
    def test_apply_success(self, mock_analyze):
        mock_analyze.return_value = '{"score": 85, "feedback": "Excellent resume."}'
        self.client.login(username="student1", password="password")
        
        response = self.client.post(f"/jobs/{self.job.id}/apply/", {
            "cover_letter": "I love Django."
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "jobs_app/application_result.html")
        self.assertContains(response, "Application Submitted Successfully")
        self.assertContains(response, "You are ELIGIBLE for this job.")
        self.assertContains(response, "85 / 100")
        self.assertContains(response, "50 / 100")
        self.assertContains(response, "Excellent resume.")
        
        # Application should be created
        self.assertTrue(ApplicationModel.objects.filter(job=self.job, applicant=self.user).exists())
        
        # Profile score should be updated
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.score, 85)

    @patch("jobs_app.views.analyze_resume")
    @patch("PyPDF2.PdfReader")
    def test_apply_with_pdf_upload(self, mock_pdf_reader, mock_analyze):
        # Mock PyPDF2 behavior
        mock_page = mock_pdf_reader.return_value.pages.__getitem__.return_value
        mock_page.extract_text.return_value = "Extracted PDF resume text"
        mock_pdf_reader.return_value.pages = [mock_page]
        
        mock_analyze.return_value = '{"score": 90, "feedback": "Nice PDF."}'
        self.client.login(username="student1", password="password")
        
        # Set profile resume to PDF file
        pdf_file = SimpleUploadedFile("resume.pdf", b"dummy pdf content", content_type="application/pdf")
        self.profile.resume = pdf_file
        self.profile.save()
        
        response = self.client.post(f"/jobs/{self.job.id}/apply/", {
            "cover_letter": "I love Django."
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "jobs_app/application_result.html")
        
        self.assertTrue(mock_analyze.called)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.score, 90)
        self.assertTrue(self.profile.resume.name.startswith("resumes/resume"))
        self.assertTrue(self.profile.resume.name.endswith(".pdf"))

    @patch("jobs_app.views.analyze_resume")
    @patch("docx.Document")
    def test_apply_with_docx_upload(self, mock_docx_doc, mock_analyze):
        # Mock python-docx behavior
        mock_para1 = mock_docx_doc.return_value.paragraphs.__getitem__.return_value
        mock_para1.text = "Extracted DOCX resume text"
        mock_docx_doc.return_value.paragraphs = [mock_para1]
        
        mock_analyze.return_value = '{"score": 95, "feedback": "Nice Word Doc."}'
        self.client.login(username="student1", password="password")
        
        # Set profile resume to DOCX file
        docx_file = SimpleUploadedFile("resume.docx", b"dummy docx content", content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        self.profile.resume = docx_file
        self.profile.save()
        
        response = self.client.post(f"/jobs/{self.job.id}/apply/", {
            "cover_letter": "I love Django."
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "jobs_app/application_result.html")
        
        self.assertTrue(mock_analyze.called)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.score, 95)
        self.assertTrue(self.profile.resume.name.startswith("resumes/resume"))
        self.assertTrue(self.profile.resume.name.endswith(".docx"))

    def test_candidate_ranking_order(self):
        # Create student 2 (high score) and student 3 (low score)
        s2 = UserModel.objects.create_user(username="student2", password="password", user_type="student")
        p2, _ = Profile.objects.get_or_create(user=s2)
        p2.score = 90
        p2.save()
        
        s3 = UserModel.objects.create_user(username="student3", password="password", user_type="student")
        p3, _ = Profile.objects.get_or_create(user=s3)
        p3.score = 60
        p3.save()
        
        # Apply for the job
        self.profile.score = 75
        self.profile.save()
        
        ApplicationModel.objects.create(job=self.job, applicant=self.user, cover_letter="I am student 1")
        ApplicationModel.objects.create(job=self.job, applicant=s2, cover_letter="I am student 2")
        ApplicationModel.objects.create(job=self.job, applicant=s3, cover_letter="I am student 3")
        
        # Check job detail recruiter view (self.recruiter is logged in)
        self.client.login(username="recruiter1", password="password")
        response = self.client.get(f"/jobs/{self.job.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["is_creator"])
        apps = list(response.context["applications"])
        
        # Expected order (score descending): student 2 (score 90), student 1 (score 75), student 3 (score 60)
        self.assertEqual(apps[0].applicant.id, s2.id)
        self.assertEqual(apps[0].rank, 1)
        self.assertEqual(apps[1].applicant.id, self.user.id)
        self.assertEqual(apps[1].rank, 2)
        self.assertEqual(apps[2].applicant.id, s3.id)
        self.assertEqual(apps[2].rank, 3)

    def test_applications_api_get_queryset(self):
        from jobs_app.views import ApplicationCreateReadView
        s2 = UserModel.objects.create_user(username="student2", password="password", user_type="student")
        p2, _ = Profile.objects.get_or_create(user=s2)
        p2.score = 95
        p2.save()
        
        s3 = UserModel.objects.create_user(username="student3", password="password", user_type="student")
        p3, _ = Profile.objects.get_or_create(user=s3)
        p3.score = 65
        p3.save()
        
        self.profile.score = 80
        self.profile.save()
        
        ApplicationModel.objects.create(job=self.job, applicant=self.user, cover_letter="I am student 1")
        ApplicationModel.objects.create(job=self.job, applicant=s2, cover_letter="I am student 2")
        ApplicationModel.objects.create(job=self.job, applicant=s3, cover_letter="I am student 3")
        
        # Instantiate view and call get_queryset()
        view = ApplicationCreateReadView()
        qs = list(view.get_queryset())
        
        # Filter by job to keep it clean
        job_qs = [q for q in qs if q.job == self.job]
        
        self.assertEqual(job_qs[0].applicant.id, s2.id)
        self.assertEqual(job_qs[0].rank, 1)
        self.assertEqual(job_qs[1].applicant.id, self.user.id)
        self.assertEqual(job_qs[1].rank, 2)
        self.assertEqual(job_qs[2].applicant.id, s3.id)
        self.assertEqual(job_qs[2].rank, 3)

    @patch("jobs_app.views.analyze_resume")
    def test_apply_with_strengths_and_improvements(self, mock_analyze):
        mock_analyze.return_value = (
            '{"score": 88, "feedback": "Nice job.", '
            '"strengths": "Strong Django skills.", '
            '"improvement_suggestions": "Learn more testing."}'
        )
        self.client.login(username="student1", password="password")
        
        response = self.client.post(f"/jobs/{self.job.id}/apply/", {
            "cover_letter": "I love Django."
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "jobs_app/application_result.html")
        self.assertContains(response, "Strong Django skills.")
        self.assertContains(response, "Learn more testing.")
        self.assertContains(response, "88 / 100")
        self.assertContains(response, "50 / 100")

    @patch("jobs_app.views.analyze_resume")
    def test_apply_with_regex_fallback(self, mock_analyze):
        mock_analyze.return_value = "Conversational prose where the Score: 92 is found."
        self.client.login(username="student1", password="password")
        
        response = self.client.post(f"/jobs/{self.job.id}/apply/", {
            "cover_letter": "I love Django."
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "jobs_app/application_result.html")
        self.assertContains(response, "92 / 100")
        self.assertContains(response, "Conversational prose where the Score: 92 is found.")
        
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.score, 92)

    @patch("jobs_app.views.analyze_resume")
    def test_apply_duplicate_submission(self, mock_analyze):
        mock_analyze.return_value = '{"score": 85, "feedback": "First application."}'
        self.client.login(username="student1", password="password")
        
        # Apply the first time (successful submission)
        response1 = self.client.post(f"/jobs/{self.job.id}/apply/", {
            "cover_letter": "First apply cover letter."
        })
        self.assertEqual(response1.status_code, 200)
        self.assertTemplateUsed(response1, "jobs_app/application_result.html")
        
        # Verify application created
        self.assertEqual(ApplicationModel.objects.filter(job=self.job, applicant=self.user).count(), 1)
        
        # Apply the second time. We patch 'exists' check in ApplicationModel queryset filter to return False
        # to bypass the view's initial check and trigger the database unique constraint IntegrityError.
        with patch("django.db.models.query.QuerySet.exists", return_value=False):
            mock_analyze.return_value = '{"score": 88, "feedback": "Second application."}'
            response2 = self.client.post(f"/jobs/{self.job.id}/apply/", {
                "cover_letter": "Second apply cover letter."
            })
            self.assertEqual(response2.status_code, 200)
            self.assertTemplateUsed(response2, "jobs_app/application_result.html")
            self.assertContains(response2, "Already Applied")
            self.assertContains(response2, "You have already submitted an application for this position! Your previous evaluation and rank remain active.")

    @patch("jobs_app.services.resume_scoring.time.sleep")
    @patch("jobs_app.services.resume_scoring.get_gemini_client")
    def test_analyze_resume_retry_loop_success(self, mock_get_client, mock_sleep):
        # Set up a mock client
        mock_client = mock_get_client.return_value
        
        # We want generate_content to raise Exception("503 Service Unavailable") twice, then succeed
        mock_response = mock_client.models.generate_content.return_value
        mock_response.text = '{"score": 90, "feedback": "Retry succeeded."}'
        
        mock_client.models.generate_content.side_effect = [
            Exception("503 Service Unavailable"),
            Exception("503 Service Unavailable"),
            mock_response
        ]
        
        from jobs_app.services.resume_scoring import analyze_resume
        result = analyze_resume("prompt text", "job description")
        
        # Verify result is correct
        self.assertEqual(result, '{"score": 90, "feedback": "Retry succeeded."}')
        
        # Verify generate_content was called 3 times
        self.assertEqual(mock_client.models.generate_content.call_count, 3)
        
        # Verify sleep was called twice with exponential delay (2s, 4s)
        self.assertEqual(mock_sleep.call_count, 2)
        mock_sleep.assert_any_call(2)
        mock_sleep.assert_any_call(4)


class JobCreationTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.recruiter = UserModel.objects.create_user(username="recruiter_test", password="password", user_type="recruiter")
        self.student = UserModel.objects.create_user(username="student_test", password="password", user_type="student")

    def test_anonymous_user_cannot_access_create_job(self):
        response = self.client.get("/jobs/create/")
        self.assertEqual(response.status_code, 302)  # Should redirect to login page

    def test_student_cannot_access_create_job(self):
        self.client.login(username="student_test", password="password")
        response = self.client.get("/jobs/create/")
        self.assertEqual(response.status_code, 403)  # Should return Forbidden

    def test_recruiter_can_access_create_job(self):
        self.client.login(username="recruiter_test", password="password")
        response = self.client.get("/jobs/create/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "jobs_app/create_job.html")

    def test_recruiter_can_create_job_successfully(self):
        self.client.login(username="recruiter_test", password="password")
        initial_count = JobModel.objects.count()
        response = self.client.post("/jobs/create/", {
            "title": "Software Architect",
            "description": "Looking for a software architect with Django experience.",
            "company_name": "InnovativeTech",
            "location": "San Francisco, CA",
            "salary": 150000,
            "minimum_score": 80
        })
        self.assertEqual(response.status_code, 302)  # Should redirect to dashboard
        self.assertEqual(JobModel.objects.count(), initial_count + 1)
        
        job = JobModel.objects.latest("created_at")
        self.assertEqual(job.title, "Software Architect")
        self.assertEqual(job.description, "Looking for a software architect with Django experience.")
        self.assertEqual(job.company_name, "InnovativeTech")
        self.assertEqual(job.location, "San Francisco, CA")
        self.assertEqual(job.salary, 150000)
        self.assertEqual(job.minimum_score, 80)
        self.assertEqual(job.created_by, self.recruiter)


class JobEditingTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.recruiter1 = UserModel.objects.create_user(username="recruiter1", password="password", user_type="recruiter")
        self.recruiter2 = UserModel.objects.create_user(username="recruiter2", password="password", user_type="recruiter")
        self.student = UserModel.objects.create_user(username="student1", password="password", user_type="student")
        
        self.job = JobModel.objects.create(
            title="Backend Dev",
            description="Django backend development.",
            company_name="TechInc",
            location="Remote",
            salary=70000,
            minimum_score=60,
            created_by=self.recruiter1
        )

    def test_anonymous_user_cannot_access_edit_job(self):
        response = self.client.get(f"/jobs/{self.job.id}/edit/")
        self.assertEqual(response.status_code, 302)  # Redirects to login

    def test_student_cannot_access_edit_job(self):
        self.client.login(username="student1", password="password")
        response = self.client.get(f"/jobs/{self.job.id}/edit/")
        self.assertEqual(response.status_code, 403)  # Forbidden

    def test_non_owner_recruiter_cannot_edit_job(self):
        self.client.login(username="recruiter2", password="password")
        response = self.client.get(f"/jobs/{self.job.id}/edit/")
        self.assertEqual(response.status_code, 403)  # Forbidden
        
        # Test POST
        response = self.client.post(f"/jobs/{self.job.id}/edit/", {
            "title": "Malicious Update",
            "description": "Trying to modify another recruiter's job.",
            "company_name": "TechInc",
            "location": "Remote",
            "salary": 70000,
            "minimum_score": 60
        })
        self.assertEqual(response.status_code, 403)
        self.job.refresh_from_db()
        self.assertNotEqual(self.job.title, "Malicious Update")

    def test_owner_recruiter_can_access_edit_job(self):
        self.client.login(username="recruiter1", password="password")
        response = self.client.get(f"/jobs/{self.job.id}/edit/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "jobs_app/edit_job.html")

    def test_owner_recruiter_can_edit_job_successfully(self):
        self.client.login(username="recruiter1", password="password")
        response = self.client.post(f"/jobs/{self.job.id}/edit/", {
            "title": "Backend Tech Lead",
            "description": "Lead Django developer role.",
            "company_name": "TechInc New",
            "location": "New York, NY",
            "salary": 120000,
            "minimum_score": 75
        })
        self.assertEqual(response.status_code, 302)  # Redirect to dashboard
        self.job.refresh_from_db()
        self.assertEqual(self.job.title, "Backend Tech Lead")
        self.assertEqual(self.job.description, "Lead Django developer role.")
        self.assertEqual(self.job.company_name, "TechInc New")
        self.assertEqual(self.job.location, "New York, NY")
        self.assertEqual(self.job.salary, 120000)
        self.assertEqual(self.job.minimum_score, 75)


class MatchAnalysisTest(TestCase):
    def setUp(self):
        self.recruiter = UserModel.objects.create_user(username="recruiter_m1", password="password", user_type="recruiter")
        self.student = UserModel.objects.create_user(username="student_m1", password="password", user_type="student")
        self.profile, _ = Profile.objects.get_or_create(user=self.student)
        
        self.job = JobModel.objects.create(
            title="Backend Dev",
            description="Django backend development.",
            company_name="TechInc",
            location="Remote",
            salary=70000,
            minimum_score=60,
            created_by=self.recruiter
        )
        self.application = ApplicationModel.objects.create(
            job=self.job,
            applicant=self.student,
            cover_letter="Interested in this job."
        )

    def test_match_analysis_processing_when_no_score(self):
        self.profile.score = 0
        self.profile.save()
        analysis = self.application.match_analysis
        self.assertEqual(analysis['text'], 'Processing')
        self.assertEqual(analysis['color'], '#6c757d')

    def test_match_analysis_excellent_match(self):
        self.profile.score = 90
        self.profile.save()
        analysis = self.application.match_analysis
        self.assertEqual(analysis['text'], 'Excellent Match')
        self.assertEqual(analysis['color'], '#28a745')
        self.assertEqual(analysis['score'], 90)

    def test_match_analysis_good_match(self):
        self.profile.score = 75
        self.profile.save()
        analysis = self.application.match_analysis
        self.assertEqual(analysis['text'], 'Good Match')
        self.assertEqual(analysis['color'], '#17a2b8')
        self.assertEqual(analysis['score'], 75)

    def test_match_analysis_low_match(self):
        self.profile.score = 50
        self.profile.save()
        analysis = self.application.match_analysis
        self.assertEqual(analysis['text'], 'Low Match')
        self.assertEqual(analysis['color'], '#ffc107')
        self.assertEqual(analysis['score'], 50)


class InterviewSchedulingTest(TestCase):
    def setUp(self):
        from django.utils import timezone
        import datetime
        self.client = Client()
        self.recruiter1 = UserModel.objects.create_user(username="recruiter1", password="password", user_type="recruiter")
        self.recruiter2 = UserModel.objects.create_user(username="recruiter2", password="password", user_type="recruiter")
        self.student = UserModel.objects.create_user(username="student1", password="password", user_type="student")
        
        self.job = JobModel.objects.create(
            title="Backend Dev",
            description="Django backend development.",
            company_name="TechInc",
            location="Remote",
            salary=70000,
            minimum_score=60,
            created_by=self.recruiter1
        )
        self.application = ApplicationModel.objects.create(
            job=self.job,
            applicant=self.student,
            cover_letter="Interested in this job."
        )

    def test_anonymous_user_cannot_access_schedule_interview(self):
        response = self.client.get(f"/applications/{self.application.id}/schedule/")
        self.assertEqual(response.status_code, 302)  # Redirects to login page

    def test_student_cannot_access_schedule_interview(self):
        self.client.login(username="student1", password="password")
        response = self.client.get(f"/applications/{self.application.id}/schedule/")
        self.assertEqual(response.status_code, 403)  # Forbidden

    def test_non_owner_recruiter_cannot_access_schedule_interview(self):
        self.client.login(username="recruiter2", password="password")
        response = self.client.get(f"/applications/{self.application.id}/schedule/")
        self.assertEqual(response.status_code, 403)  # Forbidden
        
        # Test POST
        response = self.client.post(f"/applications/{self.application.id}/schedule/", {
            "scheduled_time": "2026-06-15T10:00",
            "meeting_link": "https://meet.google.com/abc-defg-hij",
            "notes": "Bring your portfolio."
        })
        self.assertEqual(response.status_code, 403)  # Forbidden
        from jobs_app.models import InterviewModel
        self.assertFalse(InterviewModel.objects.filter(application=self.application).exists())

    def test_owner_recruiter_can_access_schedule_interview_get(self):
        self.client.login(username="recruiter1", password="password")
        response = self.client.get(f"/applications/{self.application.id}/schedule/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "jobs_app/schedule_interview.html")

    def test_owner_recruiter_can_schedule_interview_post(self):
        self.client.login(username="recruiter1", password="password")
        response = self.client.post(f"/applications/{self.application.id}/schedule/", {
            "scheduled_time": "2026-06-15T10:00",
            "meeting_link": "https://meet.google.com/abc-defg-hij",
            "notes": "Bring your portfolio."
        })
        self.assertEqual(response.status_code, 302)  # Redirects to dashboard
        from jobs_app.models import InterviewModel
        self.assertTrue(InterviewModel.objects.filter(application=self.application).exists())
        
        interview = InterviewModel.objects.get(application=self.application)
        self.assertEqual(interview.meeting_link, "https://meet.google.com/abc-defg-hij")
        self.assertEqual(interview.notes, "Bring your portfolio.")
        self.assertEqual(interview.scheduled_time.year, 2026)
        self.assertEqual(interview.scheduled_time.month, 6)
        self.assertEqual(interview.scheduled_time.day, 15)

        # Verify application status was updated to 'interview'
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, "interview")

    def test_owner_recruiter_can_reschedule_interview_post(self):
        from django.utils import timezone
        import datetime
        # Create initial interview
        from jobs_app.models import InterviewModel
        initial_time = timezone.make_aware(datetime.datetime(2026, 6, 15, 10, 0))
        interview = InterviewModel.objects.create(
            application=self.application,
            scheduled_time=initial_time,
            meeting_link="https://meet.google.com/abc-defg-hij",
            notes="Bring your portfolio."
        )
        
        self.client.login(username="recruiter1", password="password")
        response = self.client.post(f"/applications/{self.application.id}/schedule/", {
            "scheduled_time": "2026-06-16T14:30",
            "meeting_link": "https://meet.google.com/xyz-pdq-rst",
            "notes": "Updated prep notes."
        })
        self.assertEqual(response.status_code, 302)  # Redirects to dashboard
        self.assertEqual(InterviewModel.objects.filter(application=self.application).count(), 1)
        
        interview.refresh_from_db()
        self.assertEqual(interview.meeting_link, "https://meet.google.com/xyz-pdq-rst")
        self.assertEqual(interview.notes, "Updated prep notes.")
        self.assertEqual(interview.scheduled_time.day, 16)

        # Verify application status is 'interview'
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, "interview")


class MissingSkillsAnalysisTest(TestCase):
    def setUp(self):
        self.recruiter = UserModel.objects.create_user(username="recruiter_sk", password="password", user_type="recruiter")
        self.student = UserModel.objects.create_user(username="student_sk", password="password", user_type="student")
        self.profile, _ = Profile.objects.get_or_create(user=self.student)
        
        self.job = JobModel.objects.create(
            title="Backend Dev",
            description="Looking for Python, Django and PostgreSQL experience.",
            company_name="TechInc",
            location="Remote",
            salary=70000,
            minimum_score=60,
            created_by=self.recruiter
        )
        self.application = ApplicationModel.objects.create(
            job=self.job,
            applicant=self.student,
            cover_letter="Interested in this job."
        )

    def test_missing_skills_no_resume_text(self):
        self.profile.resume_text = ""
        self.profile.save()
        analysis = self.application.missing_skills_analysis
        self.assertEqual(analysis['matched'], [])
        self.assertEqual(analysis['missing'], ['No resume text found to extract profile details'])

    def test_missing_skills_matched_and_missing(self):
        # Student resume has Python and Postgresql, but missing Django
        self.profile.resume_text = "I have python coding background and PostgreSQL database admin skills."
        self.profile.save()
        analysis = self.application.missing_skills_analysis
        
        # In Job Description, we have: 'Python', 'Django', 'Postgresql'
        self.assertIn("Python", analysis['matched'])
        self.assertIn("Postgresql", analysis['matched'])
        self.assertNotIn("Django", analysis['matched'])
        
        self.assertIn("Django", analysis['missing'])
        self.assertNotIn("Python", analysis['missing'])
        self.assertNotIn("Postgresql", analysis['missing'])

    def test_missing_skills_fallback_no_common_keywords(self):
        # Job description doesn't contain any keywords from the tech_keywords list
        self.job.description = "Looking for someone to manage social media accounts."
        self.job.save()
        self.profile.resume_text = "I am a skilled developer."
        self.profile.save()
        
        analysis = self.application.missing_skills_analysis
        self.assertEqual(analysis['matched'], ['General Requirements Met'])
        self.assertEqual(analysis['missing'], [])


class QuizEngineTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.student = UserModel.objects.create_user(username="student_q1", password="password", user_type="student")
        self.profile, _ = Profile.objects.get_or_create(user=self.student)
        self.profile.score = 80
        self.profile.save()
        
        self.recruiter = UserModel.objects.create_user(username="recruiter_q1", password="password", user_type="recruiter")
        self.job = JobModel.objects.create(
            title="Python Developer Role",
            description="Django and Python backend development.",
            company_name="TechInc",
            location="Remote",
            salary=70000,
            minimum_score=60,
            created_by=self.recruiter
        )
        self.application = ApplicationModel.objects.create(
            job=self.job,
            applicant=self.student,
            cover_letter="Interested."
        )

        # Create a Python quiz
        self.quiz = QuizModel.objects.create(
            title="Python Level 1",
            category="python"
        )
        self.q1 = QuestionModel.objects.create(
            quiz=self.quiz,
            text="What is Django?",
            option_a="Framework",
            option_b="Language",
            option_c="Database",
            option_d="Browser",
            correct_option="A"
        )
        self.q2 = QuestionModel.objects.create(
            quiz=self.quiz,
            text="What is python extension?",
            option_a=".py",
            option_b=".js",
            option_c=".java",
            option_d=".cpp",
            correct_option="A"
        )

    def test_quiz_list_page(self):
        self.client.login(username="student_q1", password="password")
        response = self.client.get("/quizzes/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "jobs_app/quiz_list.html")
        self.assertIn(self.quiz, response.context["quizzes"])

    def test_take_quiz_page_get(self):
        self.client.login(username="student_q1", password="password")
        response = self.client.get(f"/quizzes/{self.quiz.id}/take/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "jobs_app/take_quiz.html")
        self.assertEqual(response.context["quiz"], self.quiz)

    def test_take_quiz_page_post_score_calculation(self):
        self.client.login(username="student_q1", password="password")
        response = self.client.post(f"/quizzes/{self.quiz.id}/take/", {
            f"question_{self.q1.id}": "A", # correct
            f"question_{self.q2.id}": "B"  # incorrect
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "jobs_app/quiz_result.html")
        self.assertEqual(response.context["score"], 50.0)
        self.assertEqual(response.context["correct"], 1)
        self.assertEqual(response.context["total"], 2)
        
        # Verify attempt is saved
        attempts = QuizAttemptModel.objects.filter(student=self.student, quiz=self.quiz)
        self.assertEqual(attempts.count(), 1)
        self.assertEqual(attempts.first().score, 50.0)

    def test_match_score_boost_applied_if_score_ge_85(self):
        # Student starts with base score 80
        self.assertEqual(self.application.match_analysis["score"], 80)
        
        # Take quiz and get 100% (>= 85%)
        QuizAttemptModel.objects.create(
            student=self.student,
            quiz=self.quiz,
            score=100.0
        )
        
        # Analyze match. Base score 80 + 10 boost = 90
        analysis = self.application.match_analysis
        self.assertEqual(analysis["score"], 90)
        self.assertEqual(analysis["text"], "Excellent Match")

    def test_match_score_boost_not_applied_if_score_lt_85(self):
        # Take quiz and get 50%
        QuizAttemptModel.objects.create(
            student=self.student,
            quiz=self.quiz,
            score=50.0
        )
        
        # Base score should remain 80 without boost
        analysis = self.application.match_analysis
        self.assertEqual(analysis["score"], 80)

    def test_match_score_boost_capped_at_100(self):
        # Base score is 95
        self.profile.score = 95
        self.profile.save()
        
        # Take quiz and get 100% (boost is +10)
        QuizAttemptModel.objects.create(
            student=self.student,
            quiz=self.quiz,
            score=100.0
        )
        
        # Score should be capped at 100, not 105
        analysis = self.application.match_analysis
        self.assertEqual(analysis["score"], 100)


class InterviewScorecardTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.recruiter1 = UserModel.objects.create_user(username="recruiter1", password="password", user_type="recruiter")
        self.recruiter2 = UserModel.objects.create_user(username="recruiter2", password="password", user_type="recruiter")
        self.student = UserModel.objects.create_user(username="student1", password="password", user_type="student")
        
        self.job = JobModel.objects.create(
            title="Backend Dev",
            description="Django backend development.",
            company_name="TechInc",
            location="Remote",
            salary=70000,
            minimum_score=60,
            created_by=self.recruiter1
        )
        self.application = ApplicationModel.objects.create(
            job=self.job,
            applicant=self.student,
            cover_letter="Interested in this job."
        )
        
    def test_owner_recruiter_can_submit_scorecard_successfully(self):
        self.client.login(username="recruiter1", password="password")
        
        # Test submitting scorecard with positive decision 'offered'
        response = self.client.post(f"/applications/{self.application.id}/scorecard/", {
            "technical_score": "5",
            "communication_score": "4",
            "problem_solving_score": "5",
            "feedback_notes": "Outstanding problem solver with clear coding style.",
            "status": "offered"
        })
        self.assertEqual(response.status_code, 302) # Redirects to dashboard
        
        # Verify scorecard created
        from jobs_app.models import InterviewScorecardModel, NotificationModel
        self.assertTrue(InterviewScorecardModel.objects.filter(application=self.application).exists())
        scorecard = InterviewScorecardModel.objects.get(application=self.application)
        self.assertEqual(scorecard.technical_score, 5)
        self.assertEqual(scorecard.communication_score, 4)
        self.assertEqual(scorecard.problem_solving_score, 5)
        self.assertEqual(scorecard.feedback_notes, "Outstanding problem solver with clear coding style.")
        
        # Verify application status was updated
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, "offered")
        
        # Verify student received notification
        self.assertTrue(NotificationModel.objects.filter(recipient=self.student, title__icontains="Offer Extended").exists())

    def test_non_owner_recruiter_cannot_submit_scorecard(self):
        self.client.login(username="recruiter2", password="password")
        
        response = self.client.post(f"/applications/{self.application.id}/scorecard/", {
            "technical_score": "4",
            "communication_score": "4",
            "problem_solving_score": "4",
            "feedback_notes": "Nice."
        })
        self.assertEqual(response.status_code, 403) # Forbidden
        from jobs_app.models import InterviewScorecardModel
        self.assertFalse(InterviewScorecardModel.objects.filter(application=self.application).exists())

    def test_student_cannot_submit_scorecard(self):
        self.client.login(username="student1", password="password")
        
        response = self.client.post(f"/applications/{self.application.id}/scorecard/", {
            "technical_score": "4",
            "communication_score": "4",
            "problem_solving_score": "4",
            "feedback_notes": "Nice."
        })
        self.assertEqual(response.status_code, 403) # Forbidden
        from jobs_app.models import InterviewScorecardModel
        self.assertFalse(InterviewScorecardModel.objects.filter(application=self.application).exists())

    def test_invalid_score_bounds_validation(self):
        self.client.login(username="recruiter1", password="password")
        
        # Test values above 5
        response = self.client.post(f"/applications/{self.application.id}/scorecard/", {
            "technical_score": "6",
            "communication_score": "4",
            "problem_solving_score": "5",
            "feedback_notes": "Invalid rating test."
        })
        self.assertEqual(response.status_code, 302) # Redirects with message
        from jobs_app.models import InterviewScorecardModel
        self.assertFalse(InterviewScorecardModel.objects.filter(application=self.application).exists())
        
        # Test values below 1
        response = self.client.post(f"/applications/{self.application.id}/scorecard/", {
            "technical_score": "5",
            "communication_score": "0",
            "problem_solving_score": "5",
            "feedback_notes": "Invalid rating test."
        })
        self.assertEqual(response.status_code, 302) # Redirects with message
        self.assertFalse(InterviewScorecardModel.objects.filter(application=self.application).exists())

    def test_rjust_repeating_template_filter(self):
        from jobs_app.templatetags.custom_filters import rjust
        self.assertEqual(rjust("★", 5), "★★★★★")
        self.assertEqual(rjust("★", 3), "★★★")
        self.assertEqual(rjust("abc", 2), "abcabc")
        self.assertEqual(rjust("★", "invalid"), "★")




