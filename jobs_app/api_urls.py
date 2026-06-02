from rest_framework.routers import DefaultRouter
from .views import JobModelViewSet

router = DefaultRouter()
router.register(r'jobs', JobModelViewSet)

urlpatterns = router.urls