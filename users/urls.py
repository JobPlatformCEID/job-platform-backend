from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    RegisterView, LoginView, LogoutView, UserMeView, UserDetailView,
    CandidateProfileView, CandidateProfileDetailView, EmployerProfileView,
    EmployerProfileDetailView, EmployerListView,
    SkillViewSet, EducationViewSet, WorkExperienceViewSet
)

router = DefaultRouter()
router.register(r'skills', SkillViewSet, basename='skill')
router.register(r'education', EducationViewSet, basename='education')
router.register(r'experience', WorkExperienceViewSet, basename='experience')

urlpatterns = [
    path('auth/register/', RegisterView.as_view()),
    path('auth/login/', LoginView.as_view()),
    path('auth/logout/', LogoutView.as_view()),
    path('users/me/', UserMeView.as_view()),
    path('users/<int:pk>/', UserDetailView.as_view()),
    path('candidates/me/', CandidateProfileView.as_view()),
    path('candidates/background/', include(router.urls)),
    path('candidates/<int:pk>/', CandidateProfileDetailView.as_view()),
    path('employers/', EmployerListView.as_view()),
    path('employers/me/', EmployerProfileView.as_view()),
    path('employers/<int:pk>/', EmployerProfileDetailView.as_view()),
]