from django.urls import path
from .views import RegisterView, LoginView, CandidateProfileView, EmployerProfileView, EmployerListView

urlpatterns = [
    path('auth/register/', RegisterView.as_view()),
    path('auth/login/', LoginView.as_view()),
    path('candidates/me/', CandidateProfileView.as_view()),
    path('employers/', EmployerListView.as_view()),
    path('employers/me/', EmployerProfileView.as_view()),
]
