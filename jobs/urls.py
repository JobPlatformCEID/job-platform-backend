from django.urls import path
from .views import (
    JobPostingListCreateView,
    JobPostingDetailView,
    JobApplicationListView,
    JobApplyView,
    JobApplicationStatusView,
)
 
urlpatterns = [
    path('jobs/', JobPostingListCreateView.as_view()),
    path('jobs/applications/', JobApplicationListView.as_view()),
    path('jobs/<int:pk>/', JobPostingDetailView.as_view()),
    path('jobs/<int:pk>/apply/', JobApplyView.as_view()),
    path('jobs/applications/<int:pk>/status/', JobApplicationStatusView.as_view()),
]
