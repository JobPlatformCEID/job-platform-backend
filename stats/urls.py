from django.urls import path
from . import views

urlpatterns = [
    path('jobs-by-title/', views.JobPostingsByTitleView.as_view(), name='jobs-by-title'),
    path('candidates-by-education/', views.CandidatesByEducationLevelView.as_view(), name='candidates-by-education'),
    path('top-skills/', views.TopSkillsView.as_view(), name='top-skills'),
    path('top-companies/', views.TopCompaniesByJobPostingsView.as_view(), name='top-companies'),
    path('avg-salary-by-title/', views.AvgSalaryByTitleView.as_view(), name='avg-salary-by-title'),
    path('jobs-over-time/', views.JobPostingsOverTimeView.as_view(), name='jobs-over-time'),
    path('remote-vs-onsite/', views.RemoteVsOnsiteView.as_view(), name='remote-vs-onsite'),
    path('jobs-by-contract-type/', views.JobsByContractTypeView.as_view(), name='jobs-by-contract-type'),
    path('avg-salary-by-contract-type/', views.AvgSalaryByContractTypeView.as_view(), name='avg-salary-by-contract-type'),
    path('most-competitive-jobs/', views.MostCompetitiveJobsView.as_view(), name='most-competitive-jobs'),
    path('salary-range-distribution/', views.SalaryRangeDistributionView.as_view(), name='salary-range-distribution'),
]