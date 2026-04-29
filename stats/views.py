from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Count
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