import logging
import json
import re
from urllib import request

from django.db import IntegrityError

from .services.resume_scoring import analyze_resume

from django.shortcuts import render, get_object_or_404, redirect
from .forms import JobCreationForm, InterviewSchedulingForm
from users_app.permissions import recruiter_required
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status, viewsets, mixins, generics

from users_app.permissions import IsStudentOrRecruiter, IsRecruiter
from users_app.authentication import CustomAuthentication

from .models import JobModel, ApplicationModel
from .serializers import ApplicationSerializer, JobSerializer

from rest_framework_simplejwt.authentication import JWTAuthentication

logger = logging.getLogger(__name__)


class ApplyJobView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, job_id):
        user = request.user
        auth_user_model = get_user_model()

        if not isinstance(user, auth_user_model):
            logger.error(
                "ApplyJobView request.user is not an instance of AUTH_USER_MODEL"
            )

        try:
            job = JobModel.objects.get(id=job_id)
        except JobModel.DoesNotExist:
            return Response(
                {"error": "Job not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        if ApplicationModel.objects.filter(
            job=job,
            applicant=request.user
        ).exists():
            return Response(
                {"error": "You have already applied for this job"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            profile = request.user.profile
        except Exception:
            return Response(
                {"error": "Profile not found"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if profile.score < job.minimum_score:
            return Response(
                {
                    "error": (
                        f"You are not eligible for this job. "
                        f"Required score: {job.minimum_score}, "
                        f"Your score: {profile.score}"
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        application = ApplicationModel.objects.create(
            job=job,
            applicant=request.user,
            cover_letter=request.data.get("cover_letter", "")
        )

        serializer = ApplicationSerializer(application)

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED
        )


def home_page(request):
    jobs = JobModel.objects.all()
    return render(request, "jobs_app/home.html", {"jobs": jobs})


def job_list(request):
    jobs = JobModel.objects.all()
    return render(request, "jobs_app/jobs.html", {"jobs": jobs})


def job_detail(request, job_id):
    job = get_object_or_404(JobModel, id=job_id)
    
    is_creator = False
    applications = None
    
    if request.user.is_authenticated:
        user = request.user
        user_type = "student"
        if hasattr(user, 'usermodel'):
            user_type = user.usermodel.user_type
        elif hasattr(user, 'user_type'):
            user_type = user.user_type
            
        if user_type == "recruiter" and job.created_by_id == user.id:
            is_creator = True
            from django.db.models import Window, F, Value
            from django.db.models.functions import RowNumber, Coalesce
            
            applications = ApplicationModel.objects.filter(job=job).select_related('applicant__profile').annotate(
                score_val=Coalesce(F('applicant__profile__score'), Value(0))
            ).annotate(
                rank=Window(
                    expression=RowNumber(),
                    order_by=[F('score_val').desc(), F('applied_at').asc()]
                )
            ).order_by('-score_val', 'applied_at')

    return render(
        request, 
        "jobs_app/job_detail.html", 
        {
            "job": job,
            "is_creator": is_creator,
            "applications": applications
        }
    )


@login_required(login_url='/login-page/')
def apply_job_page(request, job_id):
    job = get_object_or_404(JobModel, id=job_id)

    # Retrieve student profile
    try:
        profile = request.user.profile
    except Exception:
        return render(
            request,
            "jobs_app/apply_failure.html",
            {"job": job, "error": "Profile not found. Cannot evaluate eligibility."}
        )

    # Check if student has uploaded a resume in their profile
    if not profile.resume:
        return render(
            request,
            "jobs_app/apply_job.html",
            {
                "job": job,
                "error": "You must upload a resume to your profile first before applying to jobs. Please visit your Profile page."
            }
        )

    if request.method == "POST":
        # Check for duplicate application
        if ApplicationModel.objects.filter(job=job, applicant=request.user).exists():
            return render(
                request,
                "jobs_app/apply_success.html",
                {"job": job, "message": "You have already applied for this job."}
            )

        resume_text = getattr(profile, 'resume_text', '').strip()
        error_msg = None

        if not resume_text:
            file_name = profile.resume.name.lower()
            try:
                # We open the FieldFile stored on profile.resume
                profile.resume.open("rb")
                if file_name.endswith(".pdf"):
                    import PyPDF2
                    reader = PyPDF2.PdfReader(profile.resume)
                    text_parts = []
                    for page in reader.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text_parts.append(page_text)
                    resume_text = "\n".join(text_parts).strip()
                elif file_name.endswith(".docx"):
                    import docx
                    doc = docx.Document(profile.resume)
                    text_parts = []
                    for para in doc.paragraphs:
                        text_parts.append(para.text)
                    resume_text = "\n".join(text_parts).strip()
                else:
                    resume_text = profile.resume.read().decode("utf-8", errors="ignore").strip()
            except Exception as e:
                error_msg = f"Failed to extract text from your profile resume: {e}"
            finally:
                profile.resume.close()

        if error_msg:
            return render(
                request,
                "jobs_app/apply_job.html",
                {"job": job, "error": error_msg}
            )

        if not resume_text:
            return render(
                request,
                "jobs_app/apply_job.html",
                {"job": job, "error": "Your profile resume appears to contain no text."}
            )

        # Updated AI Scoring Logic using analyze_resume
        try:
            # We explicitly ask Gemini to return JSON format for parsing
            structured_prompt = (
                f"Analyze this resume against the following job description.\n\n"
                f"Resume:\n{resume_text}\n\n"
                f"Job Description:\n{job.description}\n\n"
                "Provide your evaluation completely as a valid JSON object matching this schema:\n"
                '{"score": <integer from 0 to 100>, "feedback": "<detailed feedback string>"}\n'
                "Do not include markdown blocks like ```json."
            )
            
            raw_ai_response = analyze_resume(structured_prompt, job.description)
            
            # Clean markdown wrappers if Gemini still includes them
            clean_json_text = re.sub(r'```json\s*|```', '', raw_ai_response).strip()
            
            try:
                # Parse response into structural data
                score_data = json.loads(clean_json_text)
                score = int(score_data.get("score", 0))
                feedback_val = score_data.get("feedback", "No specific feedback provided.")
                
                # Check if strengths or improvement suggestions are optionally included
                strengths_val = score_data.get("strengths", "")
                improvement_val = score_data.get("improvement_suggestions", "")
                
                if strengths_val or improvement_val:
                    feedback = {
                        "strengths": strengths_val,
                        "improvement_suggestions": improvement_val,
                        "general": feedback_val
                    }
                else:
                    feedback = feedback_val
            except Exception as json_err:
                logger.warning(f"JSON parsing failed ({json_err}). Attempting regex fallback.")
                # Regex fallback matching (?:score|rating|points)[:\s\-]*(\d+)
                match = re.search(r'(?:score|rating|points)[:\s\-]*(\d+)', raw_ai_response, re.IGNORECASE)
                if match:
                    score = int(match.group(1))
                else:
                    score = 0
                feedback = raw_ai_response
            
        except Exception as e:
            logger.error(f"AI Extraction error: {e}. Raw response: {raw_ai_response if 'raw_ai_response' in locals() else 'None'}")
            return render(
                request,
                "jobs_app/apply_failure.html",
                {"job": job, "error": f"AI Scoring parsing failed: {e}"}
            )

        # Update profile
        profile.score = score
        profile.save()

        eligible = score >= job.minimum_score

        # Create the application after passing eligibility check
        if eligible:
            try:
                ApplicationModel.objects.create(
                    job=job,
                    applicant=request.user,
                    cover_letter=request.POST.get("cover_letter")
                )
            except IntegrityError:
                return render(
                    request,
                    "jobs_app/application_result.html",
                    {
                        "job": job,
                        "eligible": True,
                        "already_applied": True,
                        "score": score,
                        "feedback": {
                            "general": "You have already submitted an application for this position! Your previous evaluation and rank remain active."
                        }
                    }
                )

        return render(
            request,
            "jobs_app/application_result.html",
            {
                "score": score,
                "minimum_score": job.minimum_score,
                "eligible": eligible,
                "feedback": feedback,
                "job": job
            }
        )

    return render(request, "jobs_app/apply_job.html", {"job": job})
class JobModelViewSet(viewsets.ModelViewSet):
    queryset = JobModel.objects.all()
    serializer_class = JobSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsRecruiter]

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            self.permission_classes = [IsStudentOrRecruiter]
        return super().get_permissions()

    def get_queryset(self):
        """For mutating actions, restrict to the recruiter's own jobs."""
        qs = super().get_queryset()
        if self.action in ["update", "partial_update", "destroy"]:
            return qs.filter(created_by=self.request.user)
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        # Double-check ownership before saving
        if serializer.instance.created_by_id != self.request.user.id:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You can only modify your own jobs.")
        serializer.save()

    def perform_destroy(self, instance):
        if instance.created_by_id != self.request.user.id:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You can only delete your own jobs.")
        instance.delete()


class ApplicationCreateReadView(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    generics.GenericAPIView
):
    serializer_class = ApplicationSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    lookup_field = "pk"

    def get_queryset(self):
        from django.db.models import Window, F, Value
        from django.db.models.functions import RowNumber, Coalesce
        
        return ApplicationModel.objects.annotate(
            score_val=Coalesce(F('applicant__profile__score'), Value(0))
        ).annotate(
            rank=Window(
                expression=RowNumber(),
                partition_by=[F('job')],
                order_by=[F('score_val').desc(), F('applied_at').asc()]
            )
        ).order_by('job', '-score_val', 'applied_at')

    def get(self, request, pk=None, *args, **kwargs):
        if pk is not None:
            return self.retrieve(request, pk=pk, *args, **kwargs)
        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(applicant=self.request.user)

    def home_page(request):
        jobs = JobModel.objects.all()
        return render(request, "jobs_app/home.html", {"jobs": jobs})


@login_required(login_url='/login-page/')
@recruiter_required
def create_job_page(request):
    if request.method == 'POST':
        form = JobCreationForm(request.POST)
        if form.is_valid():
            job = form.save(commit=False)
            from users_app.models import UserModel
            job.created_by = UserModel.objects.get(id=request.user.id)
            job.save()
            return redirect('dashboard')
    else:
        form = JobCreationForm()
    return render(request, 'jobs_app/create_job.html', {'form': form})


@login_required(login_url='/login-page/')
@recruiter_required
def edit_job_page(request, job_id):
    # Fetch the specific job or return a 404
    job = get_object_or_404(JobModel, id=job_id)
    
    # Object-level permission security check: Ensure this recruiter owns the job posting
    if job.created_by_id != request.user.id:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("Access denied. You can only edit job listings that you posted.")
        
    if request.method == 'POST':
        # Pass instance=job so Django updates the existing database row instead of creating a new one
        form = JobCreationForm(request.POST, instance=job)
        if form.is_valid():
            form.save()
            return redirect('dashboard')
    else:
        # Pre-populate the form with the current job data
        form = JobCreationForm(instance=job)
        
    return render(request, 'jobs_app/edit_job.html', {'form': form, 'job': job})


@login_required(login_url='/login-page/')
@recruiter_required
def schedule_interview_page(request, app_id):
    from .models import ApplicationModel, InterviewModel
    application = get_object_or_404(ApplicationModel, id=app_id)
    
    if application.job.created_by_id != request.user.id:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("Access denied. You can only schedule interviews for your own job postings.")
        
    try:
        interview = application.interview
    except InterviewModel.DoesNotExist:
        interview = None
    if request.method == 'POST':
        form = InterviewSchedulingForm(request.POST, instance=interview)
        if form.is_valid():
            interview = form.save(commit=False)
            interview.application = application
            interview.save()
            
            application.status = 'interview'
            application.save()
            
            # Dispatch Live Notification
            from .models import NotificationModel
            NotificationModel.objects.create(
                recipient=application.applicant,
                title="Interview Scheduled! 📅",
                message=f"A recruiter has scheduled an interview for the position: {application.job.title}."
            )
            
            return redirect('dashboard')
    else:
        form = InterviewSchedulingForm(instance=interview)
        
    return render(request, 'jobs_app/schedule_interview.html', {
        'form': form,
        'application': application,
        'interview': interview
    })


@login_required(login_url='/login-page/')
def quiz_list_page(request):
    from .models import QuizModel, QuizAttemptModel
    from django.db.models import Max
    
    quizzes = QuizModel.objects.all()
    for quiz in quizzes:
        attempts = QuizAttemptModel.objects.filter(student=request.user, quiz=quiz)
        if attempts.exists():
            quiz.highest_score = attempts.aggregate(Max('score'))['score__max']
            quiz.is_completed = True
        else:
            quiz.highest_score = None
            quiz.is_completed = False
            
    return render(request, "jobs_app/quiz_list.html", {
        "quizzes": quizzes
    })


@login_required(login_url='/login-page/')
def take_quiz_page(request, quiz_id):
    from .models import QuizModel, QuestionModel, QuizAttemptModel
    quiz = get_object_or_404(QuizModel, id=quiz_id)
    questions = quiz.questions.all()
    
    if request.method == 'POST':
        correct_count = 0
        total_questions = questions.count()
        
        for question in questions:
            submitted_answer = request.POST.get(f'question_{question.id}')
            if submitted_answer == question.correct_option:
                correct_count += 1
                
        score_percentage = (correct_count / total_questions * 100.0) if total_questions > 0 else 0.0
        
        # Save quiz attempt
        attempt = QuizAttemptModel.objects.create(
            student=request.user,
            quiz=quiz,
            score=score_percentage
        )
        
        return render(request, "jobs_app/quiz_result.html", {
            "quiz": quiz,
            "attempt": attempt,
            "score": score_percentage,
            "correct": correct_count,
            "total": total_questions
        })
        
    return render(request, "jobs_app/take_quiz.html", {
        "quiz": quiz,
        "questions": questions
    })


@login_required(login_url='/login-page/')
@recruiter_required
def submit_scorecard(request, app_id):
    from .models import ApplicationModel, InterviewScorecardModel, NotificationModel
    from django.contrib import messages
    
    application = get_object_or_404(ApplicationModel, id=app_id)
    
    # Ensure recruiter is the creator of the job posting
    if application.job.created_by_id != request.user.id:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("Access denied. You can only submit scorecards for applicants to your own job postings.")
        
    if request.method == 'POST':
        try:
            tech_score = int(request.POST.get('technical_score', 0))
            comm_score = int(request.POST.get('communication_score', 0))
            prob_score = int(request.POST.get('problem_solving_score', 0))
        except (ValueError, TypeError):
            tech_score, comm_score, prob_score = 0, 0, 0
            
        feedback_notes = request.POST.get('feedback_notes', '').strip()
        decision = request.POST.get('status')
        
        # Enforce validation (1 to 5)
        errors = []
        if not (1 <= tech_score <= 5):
            errors.append("Technical score must be between 1 and 5.")
        if not (1 <= comm_score <= 5):
            errors.append("Communication score must be between 1 and 5.")
        if not (1 <= prob_score <= 5):
            errors.append("Problem Solving score must be between 1 and 5.")
            
        if errors:
            for error in errors:
                messages.error(request, error)
            return redirect('dashboard')
            
        # Create or update scorecard record
        scorecard, created = InterviewScorecardModel.objects.update_or_create(
            application=application,
            defaults={
                'technical_score': tech_score,
                'communication_score': comm_score,
                'problem_solving_score': prob_score,
                'feedback_notes': feedback_notes,
            }
        )
        
        # Update application status if decision is offered or rejected
        if decision in ['offered', 'rejected']:
            application.status = decision
            application.save()
            
            # Send status update notification
            status_text = "Offer Extended 🎉" if decision == 'offered' else "Rejected ❌"
            NotificationModel.objects.create(
                recipient=application.applicant,
                title=f"Application Update: {status_text}",
                message=f"Your application for {application.job.title} has been {decision} after feedback scorecard submission."
            )
        else:
            # Send general feedback notification
            NotificationModel.objects.create(
                recipient=application.applicant,
                title="Interview Scorecard Submitted 📝",
                message=f"A recruiter has submitted an interview scorecard for your application to {application.job.title}."
            )
            
        messages.success(request, "Interview scorecard submitted successfully.")
        
    return redirect('dashboard')