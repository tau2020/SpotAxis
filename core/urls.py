from django.urls import path

from core import views

urlpatterns = [
    path('healthz', views.healthz, name='healthz'),
    path('internal/tasks/run', views.run_tasks, name='run_tasks'),
]
