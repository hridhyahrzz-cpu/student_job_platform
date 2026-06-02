from django.urls import path, include
from .views import ApplyJobView, JobModelViewSet, ApplicationCreateReadView
from .api_urls import router
from rest_framework.routers import SimpleRouter

router = SimpleRouter()
router.register(r'jobs', JobModelViewSet)

urlpatterns = [
    path("apply/<int:job_id>/", ApplyJobView.as_view(), name="apply-job"),
    path("applications/", ApplicationCreateReadView.as_view(), name="application-list-create"),
    path("applications/<int:pk>/", ApplicationCreateReadView.as_view(), name="application-detail"),
    path("", include(router.urls)),
]
