from rest_framework import serializers
from .models import JobPosting, JobApplication

class JobPostingSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobPosting
        fields = '__all__'
        read_only_fields = ['employer', 'created_at']

class JobApplicationSerializer(serializers.ModelSerializer):
    candidate_username = serializers.CharField(source='candidate.user.username', read_only=True)
    candidate_full_name = serializers.SerializerMethodField()
    job_title = serializers.CharField(source='job.title', read_only=True)
    company_name = serializers.CharField(source='job.employer.company_name', read_only=True)
    employer_id = serializers.IntegerField(source='job.employer.id', read_only=True)

    class Meta:
        model = JobApplication
        fields = '__all__'
        read_only_fields = ['candidate', 'created_at', 'status', 'job']

    def get_candidate_full_name(self, obj):
        name = f'{obj.candidate.user.first_name} {obj.candidate.user.last_name}'.strip()
        return name if name else obj.candidate.user.username

class JobApplicationStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobApplication
        fields = ['id','status']