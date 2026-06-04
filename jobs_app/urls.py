from django.urls import path, include
from .views import (
    ApplyJobView,
    ApplicationCreateReadView,
    job_list,
    job_detail,
    apply_job_page,
)

urlpatterns = [
    path("jobs/", job_list, name="job-list"),
    path("jobs/<int:job_id>/", job_detail, name="job-detail"),
    path("jobs/<int:job_id>/apply/", apply_job_page, name="apply-job-page"),
    path("apply/<int:job_id>/", ApplyJobView.as_view(), name="apply-job"),
    path("applications/", ApplicationCreateReadView.as_view(), name="application-list-create"),
    path("applications/<int:pk>/", ApplicationCreateReadView.as_view(), name="application-detail"),
    path("api/", include('jobs_app.api_urls')),
]
