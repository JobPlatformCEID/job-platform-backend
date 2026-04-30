from django.urls import path
from . import views

urlpatterns = [
    path('stats/jobs-by-title/', views.JobPostingsByTitleView.as_view(), name='jobs-by-title'),
    path('stats/candidates-by-education/', views.CandidatesByEducationLevelView.as_view(), name='candidates-by-education'),
    path('stats/top-skills/', views.TopSkillsView.as_view(), name='top-skills'),
    path('stats/top-companies/', views.TopCompaniesByJobPostingsView.as_view(), name='top-companies'),
    path('stats/avg-salary-by-title/', views.AvgSalaryByTitleView.as_view(), name='avg-salary-by-title'),
    path('stats/jobs-over-time/', views.JobPostingsOverTimeView.as_view(), name='jobs-over-time'),
    path('stats/remote-vs-onsite/', views.RemoteVsOnsiteView.as_view(), name='remote-vs-onsite'),
    path('stats/jobs-by-contract-type/', views.JobsByContractTypeView.as_view(), name='jobs-by-contract-type'),
    path('stats/avg-salary-by-contract-type/', views.AvgSalaryByContractTypeView.as_view(), name='avg-salary-by-contract-type'),
    path('stats/most-competitive-jobs/', views.MostCompetitiveJobsView.as_view(), name='most-competitive-jobs'),
    path('stats/salary-range-distribution/', views.SalaryRangeDistributionView.as_view(), name='salary-range-distribution'),
]