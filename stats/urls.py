from django.urls import path
from . import views

urlpatterns = [
    path('jobs-by-title/', views.JobPostingsByTitleView.as_view(), name='jobs-by-title'),
]