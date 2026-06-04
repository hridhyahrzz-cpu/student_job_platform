from django.contrib import admin
from django.urls import path, include

from .views import home_page

urlpatterns = [
    path('', home_page, name='home'),
    path('admin/', admin.site.urls),

    path('', include('jobs_app.urls')),
    path('', include('users_app.urls')),
]