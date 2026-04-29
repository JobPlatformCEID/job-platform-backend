from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Count , Avg , Case, When, IntegerField , Min, Max
from django.db.models.functions import TruncDay
from jobs.models import JobPosting
from users.models import Education, Skill
import math

class JobPostingsByTitleView(APIView):
    def get(self, request):
        data = (
            JobPosting.objects
            .values('title')
            .annotate(count=Count('id'))
            .order_by('-count')
        )
        result = [{'title': item['title'], 'count': item['count']} for item in data]
        return Response(result)

class CandidatesByEducationLevelView(APIView):
    def get(self, request):
        title = request.query_params.get('title')
        qs = Education.objects
        if title:
            qs = qs.filter(candidate__applications__job__title__icontains=title)
        data = qs.values('level').annotate(count=Count('id')).order_by('-count')
        return Response([{'level': item['level'], 'count': item['count']} for item in data])


class TopSkillsView(APIView):
    def get(self, request):
        title = request.query_params.get('title')
        qs = Skill.objects
        if title:
            qs = qs.filter(candidate__applications__job__title__icontains=title)
        data = qs.values('name').annotate(count=Count('id')).order_by('-count')[:10]
        return Response([{'skill': item['name'], 'count': item['count']} for item in data])


class TopCompaniesByJobPostingsView(APIView):
    def get(self, request):
        title = request.query_params.get('title')
        qs = JobPosting.objects
        if title:
            qs = qs.filter(title__icontains=title)
        data = qs.values('employer__company_name').annotate(count=Count('id')).order_by('-count')[:10]
        return Response([{'company': item['employer__company_name'], 'count': item['count']} for item in data])


class AvgSalaryByTitleView(APIView):
    def get(self, request):
        data = (
            JobPosting.objects
            .exclude(salary_min=None, salary_max=None)
            .values('title')
            .annotate(avg_min=Avg('salary_min'), avg_max=Avg('salary_max'))
            .order_by('-avg_max')
        )
        result = [
            {
                'title': item['title'],
                'avg_min': round(item['avg_min'] or 0, 2),
                'avg_max': round(item['avg_max'] or 0, 2),
            }
            for item in data
        ]
        return Response(result)

class JobPostingsOverTimeView(APIView):
    def get(self, request):
        title = request.query_params.get('title')
        if not title:
            return Response({'error': 'title query parameter is required'}, status=400)
        
        data = (
            JobPosting.objects
            .filter(title__icontains=title)
            .annotate(date=TruncDay('created_at'))
            .values('date')
            .annotate(count=Count('id'))
            .order_by('date')
        )
        result = [{'date': item['date'].strftime('%Y-%m-%d'), 'count': item['count']} for item in data]
        return Response(result)

class RemoteVsOnsiteView(APIView):
    def get(self, request):
        title = request.query_params.get('title')
        qs = JobPosting.objects
        if title:
            qs = qs.filter(title__icontains=title)
        data = qs.values('is_remote').annotate(count=Count('id'))
        return Response([{'type': 'Remote' if item['is_remote'] else 'On-site', 'count': item['count']} for item in data])

class JobsByContractTypeView(APIView):
    def get(self, request):
        title = request.query_params.get('title')
        qs = JobPosting.objects
        if title:
            qs = qs.filter(title__icontains=title)
        data = qs.values('contract_type').annotate(count=Count('id')).order_by('-count')
        return Response([{'contract_type': item['contract_type'], 'count': item['count']} for item in data])


class AvgSalaryByContractTypeView(APIView):
    def get(self, request):
        title = request.query_params.get('title')
        qs = JobPosting.objects.exclude(salary_min=None, salary_max=None)
        if title:
            qs = qs.filter(title__icontains=title)
        data = qs.values('contract_type').annotate(avg_min=Avg('salary_min'), avg_max=Avg('salary_max')).order_by('-avg_max')
        return Response([
            {
                'contract_type': item['contract_type'],
                'avg_min': round(item['avg_min'] or 0, 2),
                'avg_max': round(item['avg_max'] or 0, 2),
            }
            for item in data
        ])

class MostCompetitiveJobsView(APIView):
    def get(self, request):
        data = (
            JobPosting.objects
            .annotate(application_count=Count('applications'))
            .order_by('-application_count')[:10]
            .values('title', 'employer__company_name', 'application_count')
        )
        result = [
            {
                'title': item['title'],
                'company': item['employer__company_name'],
                'applications': item['application_count'],
            }
            for item in data
        ]
        return Response(result)

class SalaryRangeDistributionView(APIView):
    def get(self, request):
        title = request.query_params.get('title')
        qs = JobPosting.objects.exclude(salary_min=None)
        if title:
            qs = qs.filter(title__icontains=title)

        bounds = qs.aggregate(min_sal=Min('salary_min'), max_sal=Max('salary_min'))
        min_sal = bounds['min_sal']
        max_sal = bounds['max_sal']

        if min_sal is None or max_sal is None:
            return Response([])

        step = 1000
        start = (min_sal // step) * step
        num_buckets = math.ceil((max_sal - start) / step)

        while num_buckets > 5:
            step *= 2
            start = (min_sal // step) * step
            num_buckets = math.ceil((max_sal - start) / step)

        result = []
        current = start
        for _ in range(num_buckets):
            next_val = current + step
            is_last = next_val > max_sal
            count = qs.filter(salary_min__gte=current, salary_min__lt=next_val).count()
            label = f'{current}+' if is_last else f'{current}-{next_val}'
            result.append({'range': label, 'count': count})
            current = next_val

        return Response(result)