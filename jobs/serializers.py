from rest_framework import serializers
from rest_framework_recursive.fields import RecursiveField
from .models import (
    JobPosting, 
    JobApplication,
    JobComment,
)

class JobPostingSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobPosting
        fields = '__all__'
        read_only_fields = ['employer', 'created_at']

class JobApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobApplication
        fields = '__all__'
        read_only_fields = ['candidate', 'created_at', 'status', 'job']

class JobApplicationStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobApplication
        fields = ['id','status']

class JobCommentSerializer(serializers.ModelSerializer):
    
    replies = RecursiveField(many=True)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.deleted:
            data['content'] = '[deleted]'
            data['owner'] = None
        return data
    
    class Meta:
        ordering = ['created_at']
        model = JobComment
        fields = '__all__'
        read_only_fields = ['job', 'owner', 'created_at', 'edited', 'deleted']
