import django_filters
from .models import JobPosting, JobApplication


class JobPostingFilter(django_filters.FilterSet):
    title = django_filters.CharFilter(lookup_expr='icontains')
    location = django_filters.CharFilter(lookup_expr='icontains')
    contract_type = django_filters.CharFilter()
    is_remote = django_filters.BooleanFilter()
    is_active = django_filters.BooleanFilter()
    salary_min = django_filters.NumberFilter(lookup_expr='gte')
    salary_max = django_filters.NumberFilter(lookup_expr='lte')

    class Meta:
        model = JobPosting
        fields = [
            'title', 'location', 'contract_type',
            'is_remote', 'is_active', 'salary_min', 'salary_max',
        ]


class JobApplicationFilter(django_filters.FilterSet):
    status = django_filters.CharFilter()
    job = django_filters.NumberFilter(field_name='job', lookup_expr='exact')
    job_title = django_filters.CharFilter(field_name='job__title', lookup_expr='icontains')
    job_contract_type = django_filters.CharFilter(field_name='job__contract_type', lookup_expr='exact')
    job_location = django_filters.CharFilter(field_name='job__location', lookup_expr='icontains')
    job_is_remote = django_filters.BooleanFilter(field_name='job__is_remote')

    class Meta:
        model = JobApplication
        fields = [
            'status', 'job', 'job_title',
            'job_contract_type', 'job_location', 'job_is_remote',
        ]
