from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Count , Avg , Case, When, IntegerField , Min, Max
from django.db.models.functions import TruncDay , Lower
from jobs.models import JobPosting
from users.models import Education, Skill
import math
from rest_framework.permissions import IsAuthenticated

class JobPostingsByTitleView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        data = (
            JobPosting.objects
            .annotate(title_lower=Lower('title'))
            .values('title')
            .annotate(count=Count('id'))
            .order_by('-count')
        )
        result = [{'title': item['title'], 'count': item['count']} for item in data]
        return Response(result)

class CandidatesByEducationLevelView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        title = request.query_params.get('title')
        qs = Education.objects
        if title:
            qs = qs.filter(candidate__applications__job__title__icontains=title)
        data = qs.values('level').annotate(count=Count('id')).order_by('-count')
        return Response([{'level': item['level'], 'count': item['count']} for item in data])


class TopSkillsView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        title = request.query_params.get('title')
        qs = Skill.objects
        if title:
            qs = qs.filter(candidate__applications__job__title__icontains=title)
        data = qs.annotate(name_lower=Lower('name')).values('name').annotate(count=Count('id')).order_by('-count')[:10]
        return Response([{'skill': item['name'], 'count': item['count']} for item in data])


class TopCompaniesByJobPostingsView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        title = request.query_params.get('title')
        qs = JobPosting.objects
        if title:
            qs = qs.filter(title__icontains=title)
        data = qs.annotate(company_lower=Lower('employer__company_name')).values('employer__company_name').annotate(count=Count('id')).order_by('-count')[:10]
        return Response([{'company': item['employer__company_name'], 'count': item['count']} for item in data])


class AvgSalaryByTitleView(APIView):
    permission_classes = [IsAuthenticated]
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
    permission_classes = [IsAuthenticated]
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
        # Build a dict of date -> count, then fill in every day with 0 if missing
        date_counts = {item['date'].strftime('%Y-%m-%d'): item['count'] for item in data}
        if date_counts:
            from datetime import timedelta
            from django.utils import timezone
            start_date = min(date_counts.keys())
            end_date = max(date_counts.keys())
            start = timezone.now().strptime(start_date, '%Y-%m-%d').date()
            end = timezone.now().strptime(end_date, '%Y-%m-%d').date()
            result = []
            current = start
            while current <= end:
                key = current.strftime('%Y-%m-%d')
                result.append({'date': key, 'count': date_counts.get(key, 0)})
                current += timedelta(days=1)
        else:
            result = []
        return Response(result)

class RemoteVsOnsiteView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        title = request.query_params.get('title')
        qs = JobPosting.objects
        if title:
            qs = qs.filter(title__icontains=title)
        data = qs.values('is_remote').annotate(count=Count('id'))
        return Response([{'type': 'Remote' if item['is_remote'] else 'On-site', 'count': item['count']} for item in data])

class JobsByContractTypeView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        title = request.query_params.get('title')
        qs = JobPosting.objects
        if title:
            qs = qs.filter(title__icontains=title)
        data = qs.values('contract_type').annotate(count=Count('id')).order_by('-count')
        return Response([{'contract_type': item['contract_type'], 'count': item['count']} for item in data])


class AvgSalaryByContractTypeView(APIView):
    permission_classes = [IsAuthenticated]
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
    permission_classes = [IsAuthenticated]
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
    permission_classes = [IsAuthenticated]
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
        end = ((max_sal // step) + 1) * step

        result = []
        current = start
        while current < end:
            next_val = current + step
            count = qs.filter(salary_min__gte=current, salary_min__lt=next_val).count()
            label = f'{current}-{next_val}'
            result.append({'range': label, 'count': count})
            current = next_val

        return Response(result)