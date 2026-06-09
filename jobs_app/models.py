from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class JobModel(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()

    company_name = models.CharField(max_length=255)
    location = models.CharField(max_length=255)
    salary = models.IntegerField()

    minimum_score = models.IntegerField(default=0)

    created_by = models.ForeignKey(
        'users_app.UserModel',
        on_delete=models.CASCADE
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class ApplicationModel(models.Model):
    STATUS_CHOICES = [
        ('applied', 'Applied'),
        ('assessment', 'Online Assessment'),
        ('technical', 'Technical Interview'),
        ('hr', 'HR Round'),
        ('offered', 'Offer Extended'),
        ('rejected', 'Rejected'),
    ]

    job = models.ForeignKey(JobModel, on_delete=models.CASCADE)
    applicant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    cover_letter = models.TextField()
    status = models.CharField(
        max_length=25,
        choices=STATUS_CHOICES,
        default='applied'
    )

    applied_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("job", "applicant")

    def __str__(self):
        applicant_name = (
            self.applicant.username if self.applicant else "Anonymous"
        )
        return f"{applicant_name} - {self.job.title}"

    @property
    def match_analysis(self):
        # Fallback safety if background processing thread hasn't finished scoring yet
        try:
            profile = self.applicant.profile
        except Exception:
            return {'text': 'Processing', 'badge_class': 'badge-secondary', 'color': '#6c757d', 'score': 0}

        if not profile.score:
            return {'text': 'Processing', 'badge_class': 'badge-secondary', 'color': '#6c757d', 'score': 0}
            
        score = profile.score
        
        try:
            attempts = QuizAttemptModel.objects.filter(student=self.applicant, score__gte=85)
            has_matching_quiz = False
            job_text = (self.job.title + " " + self.job.description).lower()
            for attempt in attempts:
                category = attempt.quiz.category
                if category == 'python' and 'python' in job_text:
                    has_matching_quiz = True
                    break
                elif category == 'dsa' and ('dsa' in job_text or 'data structure' in job_text or 'algorithm' in job_text):
                    has_matching_quiz = True
                    break
                elif category == 'aptitude' and 'aptitude' in job_text:
                    has_matching_quiz = True
                    break
            if has_matching_quiz:
                score = min(score + 10, 100)
        except Exception:
            pass

        min_required = self.job.minimum_score
        
        if score >= min_required:
            if score >= 85:
                return {'text': 'Excellent Match', 'badge_class': 'badge-success', 'color': '#28a745', 'score': score}
            return {'text': 'Good Match', 'badge_class': 'badge-info', 'color': '#17a2b8', 'score': score}
        else:
            return {'text': 'Low Match', 'badge_class': 'badge-warning', 'color': '#ffc107', 'score': score}

    @property
    def missing_skills_analysis(self):
        if not self.applicant or not hasattr(self.applicant, 'profile') or not self.applicant.profile.resume_text:
            return {'matched': [], 'missing': ['No resume text found to extract profile details']}
        
        # A baseline list of technical keywords to scan for
        tech_keywords = [
            'python', 'django', 'flask', 'fastapi', 'javascript', 'react', 'vue', 'angular',
            'node', 'express', 'sql', 'mysql', 'postgresql', 'sqlite', 'mongodb', 'git', 'github',
            'aws', 'docker', 'kubernetes', 'html', 'css', 'bootstrap', 'tailwind', 'machine learning', 'ai'
        ]
        
        job_desc_lower = self.job.description.lower() if self.job and self.job.description else ""
        resume_text_lower = self.applicant.profile.resume_text.lower()
        
        # Extract key requirements mentioned in the job description
        required_skills = [skill for skill in tech_keywords if skill in job_desc_lower]
        
        matched_skills = []
        missing_skills = []
        
        for skill in required_skills:
            if skill in resume_text_lower:
                matched_skills.append(skill.title())
            else:
                missing_skills.append(skill.title())
                
        # Fallback if everything matches or no common keywords were extracted
        if not required_skills:
            return {'matched': ['General Requirements Met'], 'missing': []}
            
        return {'matched': matched_skills, 'missing': missing_skills}


class InterviewModel(models.Model):
    application = models.OneToOneField('jobs_app.ApplicationModel', on_delete=models.CASCADE, related_name='interview')
    scheduled_time = models.DateTimeField()
    meeting_link = models.URLField(max_length=500, blank=True, null=True, default="https://meet.google.com/abc-defg-hij")
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        applicant_username = (
            self.application.applicant.username if self.application and self.application.applicant else "Anonymous"
        )
        job_title = (
            self.application.job.title if self.application and self.application.job else "Unknown Job"
        )
        return f"Interview for {applicant_username} - {job_title}"


class QuizModel(models.Model):
    title = models.CharField(max_length=200)
    category = models.CharField(max_length=100, choices=[('aptitude', 'Quantitative Aptitude'), ('python', 'Python Programming'), ('dsa', 'Data Structures & Algorithms')])
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class QuestionModel(models.Model):
    quiz = models.ForeignKey(QuizModel, on_delete=models.CASCADE, related_name='questions')
    text = models.TextField()
    option_a = models.CharField(max_length=200)
    option_b = models.CharField(max_length=200)
    option_c = models.CharField(max_length=200)
    option_d = models.CharField(max_length=200)
    correct_option = models.CharField(max_length=1, choices=[('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D')])

    def __str__(self):
        return f"Q: {self.text[:50]}"


class QuizAttemptModel(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='quiz_attempts')
    quiz = models.ForeignKey(QuizModel, on_delete=models.CASCADE)
    score = models.FloatField()
    completed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        username = self.student.username if self.student else "Anonymous"
        return f"{username} - {self.quiz.title} - {self.score}%"


class NotificationModel(models.Model):
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        recipient_name = self.recipient.username if self.recipient else "Anonymous"
        return f"Alert for {recipient_name} - {self.title}"


class InterviewScorecardModel(models.Model):
    application = models.OneToOneField('ApplicationModel', on_delete=models.CASCADE, related_name='scorecard')
    technical_score = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    communication_score = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    problem_solving_score = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    feedback_notes = models.TextField(blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Scorecard for App #{self.application.id}"