import threading
import os
import logging
import PyPDF2
import docx

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login as django_login, logout as django_logout, authenticate
from rest_framework import mixins, generics, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView

from .forms import ProfileForm
from .models import UserModel, Profile
from .serializers import StudentRegisterSerializer, StudentSerializer


class CustomTokenObtainPairView(TokenObtainPairView):
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            username = request.data.get("username")
            password = request.data.get("password")
            user = authenticate(request, username=username, password=password)
            if user is not None:
                django_login(request, user)
                user_type = "student"
                if hasattr(user, 'usermodel'):
                    user_type = user.usermodel.user_type
                elif hasattr(user, 'user_type'):
                    user_type = user.user_type
                response.data["user_type"] = user_type
        return response


def logout_view(request):
    django_logout(request)
    return redirect("login-page")



def login_page(request):
    return render(request, "users_app/login.html")


def register_page(request):
    return render(request, "users_app/register.html")


@login_required(login_url='/login-page/')
def dashboard_page(request):
    user = request.user
    user_type = "student"
    if hasattr(user, 'usermodel'):
        user_type = user.usermodel.user_type
    elif hasattr(user, 'user_type'):
        user_type = user.user_type

    from jobs_app.models import NotificationModel
    unread_notifications = NotificationModel.objects.filter(recipient=user, is_read=False)

    if user_type == "recruiter":
        from jobs_app.models import JobModel, ApplicationModel, QuizAttemptModel
        from django.db.models import Window, F, Value, Q, Exists, OuterRef
        from django.db.models.functions import RowNumber, Coalesce
        
        jobs = JobModel.objects.filter(created_by_id=user.id)
        
        search_query = request.GET.get('search_query', '').strip()
        min_cgpa = request.GET.get('min_cgpa', '').strip()
        min_quiz_score = request.GET.get('min_quiz_score', '').strip()
        
        # Base applications query
        applications_qs = ApplicationModel.objects.filter(job__in=jobs).select_related('job', 'applicant__profile')
        
        # 1. Search Query filter (Keywords, skills, names)
        if search_query:
            applications_qs = applications_qs.filter(
                Q(applicant__username__icontains=search_query) |
                Q(applicant__first_name__icontains=search_query) |
                Q(applicant__last_name__icontains=search_query) |
                Q(applicant__profile__full_name__icontains=search_query) |
                Q(applicant__profile__resume_text__icontains=search_query) |
                Q(applicant__profile__bio__icontains=search_query)
            )
            
        # Annotate score_val
        applications_qs = applications_qs.annotate(
            score_val=Coalesce(F('applicant__profile__score'), Value(0))
        )
        
        # 2. Min CGPA (Profile Score) filter
        if min_cgpa:
            try:
                applications_qs = applications_qs.filter(score_val__gte=float(min_cgpa))
            except (ValueError, TypeError):
                pass
                
        # 3. Min Quiz Score filter (Quiz attempts logs)
        if min_quiz_score:
            try:
                val = float(min_quiz_score)
                attempts = QuizAttemptModel.objects.filter(student=OuterRef('applicant'), score__gte=val)
                applications_qs = applications_qs.filter(Exists(attempts))
            except (ValueError, TypeError):
                pass
                
        # Annotate rank and order by
        applications = applications_qs.annotate(
            rank=Window(
                expression=RowNumber(),
                partition_by=[F('job')],
                order_by=[F('score_val').desc(), F('applied_at').asc()]
            )
        ).order_by('job', '-score_val', 'applied_at')
        
        return render(request, "users_app/dashboard_recruiter.html", {
            "jobs": jobs,
            "applications": applications,
            "notifications": unread_notifications,
            "unread_notifications": unread_notifications,
        })
    else:
        from jobs_app.models import ApplicationModel, InterviewModel, QuizAttemptModel
        from django.utils import timezone
        from django.db.models import Max
        
        applications = ApplicationModel.objects.filter(applicant=user).select_related('job', 'applicant__profile')
        upcoming_interviews = InterviewModel.objects.filter(
            application__applicant=user,
            scheduled_time__gte=timezone.now()
        ).select_related('application__job').order_by('scheduled_time')
        
        # Calculate highest scores dynamically for charts
        categories = [
            ('python', 'Python Syntax'),
            ('dsa', 'Data Structures'),
            ('aptitude', 'Quantitative Aptitude')
        ]
        chart_labels = []
        chart_scores = []
        for cat_code, cat_name in categories:
            max_score = QuizAttemptModel.objects.filter(
                student=user,
                quiz__category=cat_code
            ).aggregate(Max('score'))['score__max']
            chart_labels.append(cat_name)
            chart_scores.append(float(max_score) if max_score is not None else 0.0)
        
        return render(request, "users_app/dashboard_student.html", {
            "applications": applications,
            "upcoming_interviews": upcoming_interviews,
            "notifications": unread_notifications,
            "unread_notifications": unread_notifications,
            "chart_labels": chart_labels,
            "chart_scores": chart_scores,
        })


@login_required(login_url='/login-page/')
def my_applications_page(request):
    from jobs_app.models import ApplicationModel
    applications = ApplicationModel.objects.filter(applicant=request.user).select_related('job', 'applicant__profile')
    return render(request, "users_app/my_applications.html", {"applications": applications})


@login_required(login_url='/login-page/')
def update_application_status(request, application_id):
    user = request.user
    user_type = "student"
    if hasattr(user, 'usermodel'):
        user_type = user.usermodel.user_type
    elif hasattr(user, 'user_type'):
        user_type = user.user_type

    if user_type != "recruiter":
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("Only recruiters can update application status.")

    from jobs_app.models import ApplicationModel
    application = get_object_or_404(ApplicationModel, id=application_id)
    
    if application.job.created_by_id != user.id:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("You do not have permission to update this application.")

    if request.method == "POST":
        if request.content_type == "application/json":
            try:
                import json
                data = json.loads(request.body)
                new_status = data.get("status")
            except Exception:
                new_status = None
        else:
            new_status = request.POST.get("status")
            
        if new_status in ["applied", "assessment", "technical", "hr", "offered", "rejected"]:
            application.status = new_status
            application.save()

            # Dispatch Notification
            from jobs_app.models import NotificationModel
            status_labels = dict(ApplicationModel.STATUS_CHOICES)
            status_display = status_labels.get(new_status, new_status)
            title = f"Application Status Update: {status_display}"
            
            if new_status == 'assessment':
                message = f"You have been moved to the Online Assessment stage for: {application.job.title}. Please check your email for test instructions."
            elif new_status == 'technical':
                message = f"Congratulations! You passed the assessment and are now scheduled for a Technical Interview for: {application.job.title}."
            elif new_status == 'hr':
                message = f"Great progress! You have advanced to the HR Round for: {application.job.title}."
            elif new_status == 'offered':
                message = f"🎉 Amazing news! You have received an Offer for the position: {application.job.title}! Check your email for details."
            elif new_status == 'rejected':
                message = f"Thank you for your interest. Unfortunately, your application for the position: {application.job.title} was not selected."
            else:
                message = f"Your application status for the position: {application.job.title} has been updated to: {status_display}."
                
            NotificationModel.objects.create(
                recipient=application.applicant,
                title=title,
                message=message
            )
            
            if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == "application/json":
                from django.http import JsonResponse
                return JsonResponse({"success": True, "status": application.status})
        else:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == "application/json":
                from django.http import JsonResponse
                return JsonResponse({"success": False, "error": "Invalid status value"}, status=400)
                
    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == "application/json":
        from django.http import JsonResponse
        return JsonResponse({"success": False, "error": "POST method required"}, status=405)
        
    return redirect("dashboard")


@login_required(login_url='/login-page/')
def mark_notification_read(request, notification_id):
    from jobs_app.models import NotificationModel
    notification = get_object_or_404(NotificationModel, id=notification_id, recipient=request.user)
    notification.is_read = True
    notification.save()
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == "application/json":
        from django.http import JsonResponse
        return JsonResponse({"success": True})
        
    referer = request.META.get('HTTP_REFERER')
    if referer:
        return redirect(referer)
    return redirect('dashboard')



def handle_background_resume(profile_id):
    """Extracts text from uploaded profiles and runs baseline scoring without blocking the main web request."""
    logger = logging.getLogger(__name__)
    from django.apps import apps
    Profile = apps.get_model('users_app', 'Profile')
    from jobs_app.services.resume_scoring import analyze_resume
    
    try:
        profile = Profile.objects.get(id=profile_id)
        if not profile.resume or not os.path.exists(profile.resume.path):
            return
            
        file_path = profile.resume.path
        ext = os.path.splitext(file_path)[1].lower()
        extracted_text = ""
        
        # Parse file based on format extension
        if ext == '.pdf':
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                extracted_text = "".join([page.extract_text() or "" for page in reader.pages])
        elif ext in ['.docx', '.doc']:
            doc = docx.Document(file_path)
            extracted_text = "\n".join([p.text for p in doc.paragraphs])
        else:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                extracted_text = f.read()
                
        if not extracted_text.strip():
            return
            
        # Update the database profile model with raw extracted text
        profile.resume_text = extracted_text
        profile.save(update_fields=['resume_text'])
        
        # Trigger an initial baseline analysis so the profile data is pre-cached
        baseline_prompt = (
            f"Analyze this resume content:\n{extracted_text}\n\n"
            "Extract the student's primary technical stack, project history, and assign a comprehensive baseline score out of 100 "
            "matching this schema:\n"
            '{"score": <int>, "feedback": "<summary>"}'
        )
        
        # This will utilize your newly implemented 503 exponential retry engine automatically!
        raw_ai_response = analyze_resume(baseline_prompt, "Baseline Profile Sync")
        
        # Parse baseline score and save to profile
        if raw_ai_response:
            import json
            import re
            clean_json_text = re.sub(r'```json\s*|```', '', raw_ai_response).strip()
            try:
                score_data = json.loads(clean_json_text)
                score = int(score_data.get("score", 0))
                profile.score = score
                profile.save(update_fields=['score'])
            except Exception as json_err:
                logger.warning(f"Baseline JSON parsing failed ({json_err}). Attempting regex fallback.")
                match = re.search(r'(?:score|rating|points)[:\s\-]*(\d+)', raw_ai_response, re.IGNORECASE)
                if match:
                    score = int(match.group(1))
                    profile.score = score
                    profile.save(update_fields=['score'])
        
    except Exception as e:
        logger.error(f"Background thread processing crashed for Profile ID {profile_id}: {str(e)}")


@login_required(login_url='/login-page/')
def profile_page(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            profile = form.save(commit=False)
            profile.user = request.user
            profile.save()
            
            if 'resume' in request.FILES:
                # Clear existing pre-extracted text and score to avoid using stale data
                profile.resume_text = ""
                profile.score = 0
                profile.save(update_fields=['resume_text', 'score'])
                
                # Instantiating a daemon thread guarantees it detaches cleanly from the HTTP response loop
                download_thread = threading.Thread(target=handle_background_resume, args=(profile.id,))
                download_thread.daemon = True
                download_thread.start()
                
            success_message = 'Profile updated successfully.'
            return render(request, 'users_app/profile.html', {
                'form': form,
                'profile': profile,
                'success_message': success_message,
            })
        error_message = 'Please fix the errors below.'
        return render(request, 'users_app/profile.html', {
            'form': form,
            'profile': profile,
            'error_message': error_message,
        })

    form = ProfileForm(instance=profile)
    return render(request, 'users_app/profile.html', {
        'form': form,
        'profile': profile,
    })


@api_view(["POST"])
def register_student(request):

    serializer = StudentRegisterSerializer(data=request.data)

    if serializer.is_valid():
        serializer.save()

        return Response(
            {"message": "Student registered successfully"},
            status=status.HTTP_201_CREATED
        )

    return Response(
        serializer.errors,
        status=status.HTTP_400_BAD_REQUEST
    )


class StudentListRetrieveView(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    generics.GenericAPIView
):
    """
    List all students or retrieve a single student by id.
    """
    queryset = UserModel.objects.filter(user_type="student")
    serializer_class = StudentSerializer
    lookup_field = "pk"

    def get(self, request, pk=None, *args, **kwargs):
        if pk is not None:
            return self.retrieve(request, pk=pk, *args, **kwargs)
        return self.list(request, *args, **kwargs)
