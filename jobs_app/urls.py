from django.urls import path, include
from .views import (
    ApplyJobView,
    ApplicationCreateReadView,
    job_list,
    job_detail,
    apply_job_page,
    create_job_page,
    edit_job_page,
    schedule_interview_page,
    quiz_list_page,
    take_quiz_page,
    submit_scorecard,
)

urlpatterns = [
    path("jobs/", job_list, name="job-list"),
    path("jobs/create/", create_job_page, name="create_job"),
    path("jobs/<int:job_id>/", job_detail, name="job-detail"),
    path("jobs/<int:job_id>/edit/", edit_job_page, name="edit_job"),
    path("jobs/<int:job_id>/apply/", apply_job_page, name="apply-job-page"),
    path("apply/<int:job_id>/", ApplyJobView.as_view(), name="apply-job"),
    path("applications/", ApplicationCreateReadView.as_view(), name="application-list-create"),
    path("applications/<int:pk>/", ApplicationCreateReadView.as_view(), name="application-detail"),
    path("applications/<int:app_id>/schedule/", schedule_interview_page, name="schedule_interview"),
    path("applications/<int:app_id>/scorecard/", submit_scorecard, name="submit_scorecard"),
    path("quizzes/", quiz_list_page, name="quiz_list"),
    path("quizzes/<int:quiz_id>/take/", take_quiz_page, name="take_quiz"),
    path("api/", include('jobs_app.api_urls')),
]
