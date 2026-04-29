from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Count , Avg
from django.db.models.functions import TruncDay
from jobs.models import JobPosting
from users.models import Education, Skill

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
        data = (
            Education.objects
            .values('level')
            .annotate(count=Count('id'))
            .order_by('-count')
        )
        result = [{'level': item['level'], 'count': item['count']} for item in data]
        return Response(result)

class TopSkillsView(APIView):
    def get(self, request):
        data = (
            Skill.objects
            .values('name')
            .annotate(count=Count('id'))
            .order_by('-count')[:10]
        )
        result = [{'skill': item['name'], 'count': item['count']} for item in data]
        return Response(result)

class TopCompaniesByJobPostingsView(APIView):
    def get(self, request):
        data = (
            JobPosting.objects
            .values('employer__company_name')
            .annotate(count=Count('id'))
            .order_by('-count')[:10]
        )
        result = [{'company': item['employer__company_name'], 'count': item['count']} for item in data]
        return Response(result)

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