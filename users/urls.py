from django.urls import path
from .views import (
    RegisterView, LoginView, LogoutView,
    UserNameView,
    CandidateProfileView, EmployerProfileView,
    WorkExperienceListCreateView, WorkExperienceDetailView,
    EducationListCreateView, EducationDetailView,
    SkillListCreateView, SkillDetailView,
    CertificationListCreateView, CertificationDetailView,
    ProjectListCreateView, ProjectDetailView, AvatarUpdateView
)

urlpatterns = [
    # Auth 
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/',    LoginView.as_view(),    name='login'),
    path('auth/logout/',   LogoutView.as_view(),   name='logout'),
    path('me/name/', UserNameView.as_view(), name='user-name'),

    # Profiles (matched to what tests expect)
    path('candidates/me/', CandidateProfileView.as_view(), name='candidate-profile'),
    path('employers/me/',  EmployerProfileView.as_view(),  name='employer-profile'),
    path('me/avatar/', AvatarUpdateView.as_view() , name='user-avatar'),

    # Work Experience
    path('work-experience/',          WorkExperienceListCreateView.as_view(), name='work-experience-list'),
    path('work-experience/<int:pk>/', WorkExperienceDetailView.as_view(),     name='work-experience-detail'),

    # Education 
    path('education/',          EducationListCreateView.as_view(), name='education-list'),
    path('education/<int:pk>/', EducationDetailView.as_view(),     name='education-detail'),

    # Skills
    path('skills/',          SkillListCreateView.as_view(), name='skill-list'),
    path('skills/<int:pk>/', SkillDetailView.as_view(),     name='skill-detail'),

    #Certifications
    path('certifications/',          CertificationListCreateView.as_view(), name='certification-list'),
    path('certifications/<int:pk>/', CertificationDetailView.as_view(),     name='certification-detail'),

    # Projects
    path('projects/',          ProjectListCreateView.as_view(), name='project-list'),
    path('projects/<int:pk>/', ProjectDetailView.as_view(),     name='project-detail'),
]