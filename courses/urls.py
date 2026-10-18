from django.urls import path, include
from . import views
urlpatterns = [path('recordings/', views.recordings, name='recordings'), path('recordings/<int:pk>/', views.recording_detail, name='recording_detail'), path('recordings/<int:pk>/stream/', views.recording_stream, name='recording_stream'), path('', views.home, name='home'), path('lessons/', views.lessons, name='lessons'), path('progress/', views.progress, name='progress'), path('sessions/<int:pk>/', views.session_detail, name='session_detail')]
urlpatterns += [path('materials/<int:pk>/',views.material_detail,name='material_detail'),path('materials/<int:pk>/media/<slug:key>/',views.material_stream,name='material_stream')]

urlpatterns += [path('rewards/summary/',views.reward_summary,name='reward_summary')]
urlpatterns += [path('resources/<int:pk>/stream/',views.resource_stream,name='resource_stream')]
public_patterns=list(urlpatterns)
urlpatterns += [path('s/<slug:student_slug>/',include((public_patterns,'student'),namespace='student'))]
