from django.urls import path, include
from .views import ApplyJobView, JobModelViewSet
from .api_urls import router
from rest_framework.routers import SimpleRouter

router = SimpleRouter()
router.register(r'jobs', JobModelViewSet)

urlpatterns = [
    path("apply/<int:job_id>/", ApplyJobView.as_view(), name="apply-job"),
    path("", include(router.urls)),
]
