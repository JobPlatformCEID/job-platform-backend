from django.urls import path
from . import views

urlpatterns = [
    path('jobs-by-title/', views.JobPostingsByTitleView.as_view(), name='jobs-by-title'),
    path('candidates-by-education/', views.CandidatesByEducationLevelView.as_view(), name='candidates-by-education'),
    path('top-skills/', views.TopSkillsView.as_view(), name='top-skills'),
    path('top-companies/', views.TopCompaniesByJobPostingsView.as_view(), name='top-companies'),
    path('avg-salary-by-title/', views.AvgSalaryByTitleView.as_view(), name='avg-salary-by-title'),
]