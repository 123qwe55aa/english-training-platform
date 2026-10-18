from django.contrib import admin
from django.urls import path, include
from .health import health
urlpatterns = [path('health/', health, name='health'), path('admin/', admin.site.urls), path('', include('courses.urls'))]
